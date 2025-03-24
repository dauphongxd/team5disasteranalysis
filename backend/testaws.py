import boto3
import os
from dotenv import load_dotenv
import time
from concurrent.futures import ThreadPoolExecutor
from prettytable import PrettyTable  # Optional: for nicer table output

# Load environment variables
load_dotenv('.env')

# Print environment variables (with secrets partially hidden)
access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', '')
region = os.getenv('AWS_REGION', 'us-east-1')

print(f"AWS_ACCESS_KEY_ID: {access_key[:4]}{'*' * (len(access_key) - 4) if len(access_key) > 4 else ''}")
print(f"AWS_SECRET_ACCESS_KEY: {secret_key[:4]}{'*' * (len(secret_key) - 4) if len(secret_key) > 4 else ''}")
print(f"AWS_REGION: {region}")


def count_items_in_table(dynamodb, table_name):
    """
    Counts the total number of items in a DynamoDB table.

    Args:
        dynamodb: boto3 dynamodb resource
        table_name: name of the table to count

    Returns:
        int: total count of items in the table
    """
    try:
        table = dynamodb.Table(table_name)

        # For small tables, we can do a simple scan with Select='COUNT'
        response = table.scan(Select='COUNT')
        count = response['Count']

        # Handle pagination for large tables
        while 'LastEvaluatedKey' in response:
            print(f"  Continuing scan for {table_name} - found {count} items so far...")
            response = table.scan(
                Select='COUNT',
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            count += response['Count']

        return count
    except Exception as e:
        print(f"Error counting items in {table_name}: {e}")
        return -1  # Error indicator


def get_table_size_info(dynamodb, table_name):
    """
    Get additional size information about the table (if available)

    Args:
        dynamodb: boto3 dynamodb resource
        table_name: name of the table

    Returns:
        dict: information about table size
    """
    try:
        client = dynamodb.meta.client
        response = client.describe_table(TableName=table_name)

        # Get table size in bytes if available
        if 'TableSizeBytes' in response.get('Table', {}):
            size_bytes = response['Table']['TableSizeBytes']
            size_mb = size_bytes / (1024 * 1024)
            return {
                'size_bytes': size_bytes,
                'size_mb': round(size_mb, 2)
            }
        return {}
    except Exception as e:
        print(f"Error getting size info for {table_name}: {e}")
        return {}


def analyze_table(dynamodb, table_name):
    """Analyze a single table and return its stats"""
    start_time = time.time()
    count = count_items_in_table(dynamodb, table_name)
    size_info = get_table_size_info(dynamodb, table_name)
    time_taken = round(time.time() - start_time, 2)

    return {
        'name': table_name,
        'count': count,
        'size_bytes': size_info.get('size_bytes', 'N/A'),
        'size_mb': size_info.get('size_mb', 'N/A'),
        'time_taken': time_taken
    }


try:
    # Connect to AWS
    print("\nTrying to connect to AWS...")
    dynamodb = boto3.resource('dynamodb',
                              region_name=region,
                              aws_access_key_id=access_key,
                              aws_secret_access_key=secret_key)

    # List tables to test connection
    print("\nListing DynamoDB tables:")
    tables = list(dynamodb.tables.all())
    table_names = [table.name for table in tables]
    print(f"Found {len(tables)} tables:")
    for table in tables:
        print(f"- {table.name}")

    print("\nAWS credentials are working correctly!")

    # Count items in each table
    print("\nCounting items in each table:")

    table_stats = []

    # Option 1: Sequential processing
    for table_name in table_names:
        print(f"Counting items in {table_name}...")
        stats = analyze_table(dynamodb, table_name)
        table_stats.append(stats)
        print(f"  {stats['count']} items found in {stats['time_taken']}s")

    # Option 2: Parallel processing (faster for many tables)
    # Uncomment the following code to use parallel processing instead
    """
    with ThreadPoolExecutor(max_workers=min(10, len(table_names))) as executor:
        print("Starting parallel table analysis...")
        table_stats = list(executor.map(
            lambda name: analyze_table(dynamodb, name), 
            table_names
        ))
    """

    # Print summary in a nice table
    try:
        # Using PrettyTable for nice formatting
        summary_table = PrettyTable()
        summary_table.field_names = ["Table Name", "Item Count", "Size (MB)", "Time (s)"]

        for stat in table_stats:
            summary_table.add_row([
                stat['name'],
                stat['count'],
                stat['size_mb'] if stat['size_mb'] != 'N/A' else 'N/A',
                stat['time_taken']
            ])

        print("\nTable Summary:")
        print(summary_table)

    except ImportError:
        # Fallback if PrettyTable is not installed
        print("\nTable Summary:")
        print(f"{'Table Name':<30} {'Item Count':<15} {'Size (MB)':<15} {'Time (s)':<10}")
        print("-" * 70)

        for stat in table_stats:
            size_str = f"{stat['size_mb']} MB" if stat['size_mb'] != 'N/A' else 'N/A'
            print(f"{stat['name']:<30} {stat['count']:<15} {size_str:<15} {stat['time_taken']:<10}")

    # Calculate and display totals
    total_items = sum(stat['count'] for stat in table_stats if stat['count'] >= 0)
    total_size_mb = sum(stat['size_mb'] for stat in table_stats if stat['size_mb'] != 'N/A')

    print(f"\nTotal items across all tables: {total_items}")
    print(f"Total storage used: {round(total_size_mb, 2)} MB")

except Exception as e:
    print(f"\nError connecting to AWS: {e}")

    # Check if it's a credentials issue
    if "security token" in str(e).lower() or "credentials" in str(e).lower():
        print("\nThis appears to be a credentials issue. Possible solutions:")
        print("1. Check that your AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are correct")
        print("2. Make sure your IAM user has permissions for DynamoDB")
        print("3. Try creating a new IAM user with AmazonDynamoDBFullAccess policy")
    elif "region" in str(e).lower():
        print("\nThis appears to be a region issue. Make sure you've specified the correct AWS_REGION")
    else:
        print(
            "For further troubleshooting, visit: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GettingStarted.Python.html")
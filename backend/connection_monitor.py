"""
Tool to monitor WebSocket connections in the DisasterFeed_Connections table
"""
import boto3
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables
load_dotenv('.env')

# Initialize DynamoDB client
region = os.getenv('AWS_REGION', 'us-east-1')
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

dynamodb = boto3.resource('dynamodb',
                          region_name=region,
                          aws_access_key_id=aws_access_key_id,
                          aws_secret_access_key=aws_secret_access_key)

# Table name
CONNECTIONS_TABLE = 'DisasterFeed_Connections'
connections_table = dynamodb.Table(CONNECTIONS_TABLE)


def get_active_connections():
    """Get all active connections from the DynamoDB table"""
    try:
        response = connections_table.scan()
        return response.get('Items', [])
    except Exception as e:
        print(f"Error getting connections: {e}")
        return []


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def format_time(timestamp):
    """Format timestamp for display"""
    if timestamp.isdigit():
        # Convert epoch time to datetime
        return datetime.fromtimestamp(int(timestamp) / 1000).strftime('%Y-%m-%d %H:%M:%S')
    try:
        # Try to parse as ISO format
        return datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp  # Return as is if we can't parse it


def monitor_connections(refresh_interval=5):
    """Monitor active connections with periodic refresh"""
    try:
        while True:
            clear_screen()
            connections = get_active_connections()

            if not connections:
                print("No active WebSocket connections found")
            else:
                # Prepare data for tabular display
                table_data = []
                for conn in connections:
                    # Format the connected_at time if it exists
                    connected_at = conn.get('created_at', 'Unknown')
                    if connected_at != 'Unknown':
                        connected_at = format_time(connected_at)

                    # Get subscription information
                    subscription = conn.get('disasterType', 'all')

                    # Add row to table data
                    table_data.append([
                        conn['connectionId'][:10] + '...',  # Truncate long IDs
                        connected_at,
                        subscription,
                        conn.get('status', 'unknown')
                    ])

                # Display table
                print(f"\n📊 Active WebSocket Connections: {len(connections)}")
                print(tabulate(
                    table_data,
                    headers=['Connection ID', 'Connected At', 'Subscription', 'Status'],
                    tablefmt='pretty'
                ))

            # Show instructions
            print(f"\n🔄 Refreshing every {refresh_interval} seconds... (Press Ctrl+C to exit)")
            print("📱 Open your web app to create new connections")

            # Wait for next refresh
            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        print(f"\nError monitoring connections: {e}")


if __name__ == "__main__":
    try:
        refresh = int(input("Refresh interval in seconds (default 5): ") or "5")
    except ValueError:
        refresh = 5

    print(f"Starting WebSocket connection monitor with {refresh}s refresh interval...")
    monitor_connections(refresh)
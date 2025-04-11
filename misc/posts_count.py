import json
import os
from datetime import datetime


def analyze_disaster_posts(input_file='disaster_posts.json', threshold=0.95, save_output=True):
    """
    Analyze disaster posts JSON file, identifying high confidence posts.

    Args:
        input_file (str): Path to the JSON file containing disaster posts
        threshold (float): Confidence score threshold (default: 0.95)
        save_output (bool): Whether to save high confidence posts to a new file
    """
    print(f"\n=== DISASTER POSTS ANALYSIS ===")
    print(f"Analyzing file: {input_file}")
    print(f"Confidence threshold: {threshold}")
    print("=" * 30)

    try:
        # Check if file exists
        if not os.path.exists(input_file):
            print(f"Error: File '{input_file}' not found.")
            return

        # Load the JSON data
        with open(input_file, 'r', encoding='utf-8') as f:
            try:
                posts = json.load(f)
                print(f"Successfully loaded JSON data.")
            except json.JSONDecodeError:
                print(f"Error: '{input_file}' contains invalid JSON.")
                return

        # Ensure it's a list of posts
        if not isinstance(posts, list):
            print(f"Error: Expected a list of posts, but got {type(posts)}.")
            return

        # Count total posts
        total_posts = len(posts)
        print(f"\nTotal posts: {total_posts}")

        # Find high confidence posts
        high_confidence_posts = []
        for post in posts:
            confidence = post.get('confidence_score', 0)
            if confidence > threshold:
                high_confidence_posts.append(post)

        # Count high confidence posts
        high_confidence_count = len(high_confidence_posts)

        print(f"Posts with confidence score > {threshold}: {high_confidence_count}")
        if total_posts > 0:
            print(f"Percentage: {high_confidence_count / total_posts * 100:.2f}%")

        # Group by disaster type
        disaster_types = {}
        for post in high_confidence_posts:
            d_type = post.get('predicted_disaster_type', 'unknown')
            if d_type in disaster_types:
                disaster_types[d_type] += 1
            else:
                disaster_types[d_type] = 1

        # Group by keyword match
        keywords = {}
        for post in high_confidence_posts:
            keyword = post.get('keyword_match', 'unknown')
            if keyword in keywords:
                keywords[keyword] += 1
            else:
                keywords[keyword] = 1

        # Print breakdown by disaster type
        if disaster_types:
            print("\nHigh confidence posts by disaster type:")
            for d_type, count in sorted(disaster_types.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {d_type}: {count} posts ({count / high_confidence_count * 100:.1f}%)")

        # Print breakdown by keyword match
        if keywords:
            print("\nHigh confidence posts by keyword match:")
            for keyword, count in sorted(keywords.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {keyword}: {count} posts ({count / high_confidence_count * 100:.1f}%)")

        # Display details of high confidence posts
        if high_confidence_posts:
            print("\nHigh confidence posts details:")
            for i, post in enumerate(high_confidence_posts, 1):
                print(
                    f"\n[{i}] Score: {post.get('confidence_score'):.4f} | Type: {post.get('predicted_disaster_type')}")
                print(f"    Text: {post.get('text')}")
                print(f"    Keyword: {post.get('keyword_match')}")

        # Save high confidence posts to a new file if requested
        if save_output and high_confidence_posts:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"high_confidence_posts_{timestamp}.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(high_confidence_posts, f, indent=2, ensure_ascii=False)

            print(f"\nSaved {high_confidence_count} high confidence posts to: {output_file}")

        return total_posts, high_confidence_count, high_confidence_posts

    except Exception as e:
        print(f"Error: {str(e)}")
        return None, None, None


if __name__ == "__main__":
    # You can specify a different file or threshold here if needed
    analyze_disaster_posts(input_file='disaster_posts.json', threshold=0.95)
import time
from atproto import Client, models
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoConfig
import torch.nn.functional as F
import emoji
import datetime
import json  # Import json module for JSON file handling
from dotenv import load_dotenv
import os

# 1. Bluesky Configuration with env
load_dotenv('disasterweb.env')

FEED_URI = 'at://did:plc:qiknc4t5rq7yngvz7g4aezq7/app.bsky.feed.generator/aaaelfwqlfugs'

# 2. Initialize AI Model
MODEL_PATH = r'D:\School Stuff\UTD\2025\Project\Model\checkpoint-31710\checkpoint-31710'
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)

# Load the config to access id2label
config = AutoConfig.from_pretrained(MODEL_PATH)
id2label = config.id2label  # Access the id2label mapping

# 3. Bluesky Client Setup
client = Client()
client.login(os.getenv('API_HANDLE'), os.getenv('API_PW'))

# 4. Real-time Processing Function
def process_feed():
    last_processed = None
    log_file_path = "disaster_feed_log_base.txt"
    json_file_path = "posts.json"  # JSON file to store posts for the website

    # Open the log file and JSON file
    log_file = open(log_file_path, "a", encoding='utf-8')
    posts_data = []  # List to store post data for JSON

    # Rate limiting variables
    posts_processed_in_last_minute = 0
    last_minute_start_time = time.time()

    try:
        # Enter the main loop to process new posts in real-time
        while True:
            response = client.app.bsky.feed.get_feed(
                params={
                    'feed': FEED_URI,
                    'limit': 10,
                    'cursor': last_processed
                }
            )

            if not response.feed:
                break

            for post in response.feed:
                try:
                    # Check if we've processed 5 posts in the last minute
                    if posts_processed_in_last_minute >= 5:
                        # Calculate the time remaining in the current minute
                        time_elapsed = time.time() - last_minute_start_time
                        if time_elapsed < 60:
                            # Wait for the remaining time in the minute
                            time.sleep(60 - time_elapsed)
                        # Reset the counter and timer
                        posts_processed_in_last_minute = 0
                        last_minute_start_time = time.time()

                    if last_processed and post.post.indexed_at <= last_processed:
                        continue

                    # Extract post details
                    uri = post.post.uri  # Unique identifier (URI) of the post
                    handle = post.post.author.handle  # Poster's handle
                    display_name = post.post.author.display_name  # Poster's display name
                    text = post.post.record.text  # Text of the post
                    timestamp = post.post.record.created_at  # Timestamp
                    avatar = post.post.author.avatar  # Profile picture URL

                    # Extract media URLs (if any)
                    media_urls = []
                    if hasattr(post.post.record, 'embed') and hasattr(post.post.record.embed, 'images'):
                        for image in post.post.record.embed.images:
                            # Extract the image URL from the BlobRef object
                            if hasattr(image, 'image') and hasattr(image.image, 'ref') and hasattr(image.image.ref, 'link'):
                                # Construct the full image URL using the link
                                image_url = f"https://cdn.bsky.app/img/feed_fullsize/{image.image.ref.link}"
                                media_urls.append(image_url)

                    # Demojize text for model input
                    demojized_text = emoji.demojize(text)

                    # Tokenize and predict
                    inputs = tokenizer(demojized_text, return_tensors="pt", truncation=True, padding=True)
                    outputs = model(**inputs)
                    probabilities = F.softmax(outputs.logits, dim=-1)
                    predicted_index = probabilities.argmax().item()
                    predicted_label = id2label[predicted_index]
                    confidence_score = probabilities[0, predicted_index].item()

                    threshold = 0.9  # Example threshold - adjust as needed

                    # Prepare post data for JSON
                    post_data = {
                        "uri": uri,
                        "handle": handle,
                        "display_name": display_name,
                        "text": text,
                        "demojized_text": demojized_text,
                        "timestamp": timestamp,
                        "avatar": avatar,
                        "media": media_urls,
                        "predicted_disaster_type": predicted_label,
                        "confidence_score": confidence_score,
                        "is_disaster": predicted_label != "unknown" and confidence_score >= threshold
                    }

                    # Append post data to the list
                    posts_data.append(post_data)

                    # Log the post
                    log_entry = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] New post: {demojized_text}\n"
                    if predicted_label == "unknown" or confidence_score < threshold:
                        log_entry += f"Predicted disaster type: Uncertain/Non-Disaster (Confidence: {confidence_score:.4f})\n\n"
                        print(f"New post: {text}") # Print ORIGINAL text to console (with emojis)
                        print(f"Predicted disaster type: Uncertain/Non-Disaster (Confidence: {confidence_score:.4f})\n")
                    else:
                        log_entry += f"Predicted disaster type: {predicted_label} (Confidence: {confidence_score:.4f})\n\n"
                        print(f"New post: {text}") # Print ORIGINAL text to console (with emojis)
                        print(f"Predicted disaster type: {predicted_label} (Confidence: {confidence_score:.4f})\n")

                    log_file.write(log_entry)

                    # Update last_processed
                    last_processed = post.post.indexed_at

                    # Increment the posts processed counter
                    posts_processed_in_last_minute += 1

                except Exception as e:
                    print(f"Error processing post: {e}")
                    continue

            # Save the posts data to a JSON file
            with open(json_file_path, "w", encoding="utf-8") as json_file:
                json.dump(posts_data, json_file, indent=4, ensure_ascii=False)

            time.sleep(600)
    finally:
        log_file.close()


if __name__ == "__main__":
    process_feed()

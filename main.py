import time
from atproto import Client, models
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoConfig # Import AutoConfig
import torch.nn.functional as F
import emoji
import datetime

# 1. Bluesky Configuration (No changes here)
BLUESKY_HANDLE = 'chienthann.bsky.social'
BLUESKY_APP_PASSWORD = '....'
FEED_URI = 'at://did:plc:.../app.bsky.feed.generator/aaaelfwqlfugs'

# 2. Initialize AI Model
MODEL_PATH = r'F:\AI TRAINING\results_disaster_type_roberta_fulldata\checkpoint-31710'
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)

# Load the config to access id2label
config = AutoConfig.from_pretrained(MODEL_PATH)
id2label = config.id2label # Access the id2label mapping

# 3. Bluesky Client Setup (No changes here)
client = Client()
client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)


# 4. Real-time Processing Function
def process_feed():
    last_processed = None
    log_file_path = "disaster_feed_log_base.txt"
    log_file = open(log_file_path, "a", encoding='utf-8')

    try:
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

            for post in (response.feed):
                if last_processed and post.post.indexed_at <= last_processed:
                    continue

                text = post.post.record.text # Original text with emojis
                demojized_text = emoji.demojize(text) # Text representation for logging & model input

                inputs = tokenizer(demojized_text, return_tensors="pt", truncation=True, padding=True) # Tokenize demojized text - Removed candidate_labels
                outputs = model(**inputs)
                probabilities = F.softmax(outputs.logits, dim=-1) # Softmax probabilities for all classes

                predicted_index = probabilities.argmax().item() # Get index of class with highest probability (across all classes)
                predicted_label = id2label[predicted_index] # Map index to label
                confidence_score = probabilities[0, predicted_index].item() # Get confidence score for predicted class

                threshold = 0.9 # Example threshold - adjust as needed

                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_entry = f"[{timestamp}] New post: {demojized_text}\n" # Log DEMOJIZED text
                if predicted_label == "unknown" or confidence_score < threshold: # Check for "unknown" or low confidence
                    log_entry += f"[{timestamp}] Predicted disaster type: Uncertain/Non-Disaster (Confidence: {confidence_score:.4f})\n\n"
                    print(f"New post: {text}") # Print ORIGINAL text to console (with emojis)
                    print(f"Predicted disaster type: Uncertain/Non-Disaster (Confidence: {confidence_score:.4f})\n")
                else:
                    log_entry += f"[{timestamp}] Predicted disaster type: {predicted_label} (Confidence: {confidence_score:.4f})\n\n"
                    print(f"New post: {text}") # Print ORIGINAL text to console (with emojis)
                    print(f"Predicted disaster type: {predicted_label} (Confidence: {confidence_score:.4f})\n")

                log_file.write(log_entry)

                last_processed = post.post.indexed_at

            time.sleep(600)
    finally:
        log_file.close()



if __name__ == "__main__":
    process_feed()
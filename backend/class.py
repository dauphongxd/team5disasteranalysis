from bluesky.client import BlueskyClient
from dynamodb.db import DisasterDatabase

import re
from transformers import AutoTokenizer, AutoModelForSequenceClassification, RobertaConfig
import torch.nn.functional as F
from dotenv import load_dotenv
import logging
from dotenv import load_dotenv
import os
from os.path import join, dirname

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("disaster_feed.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv("./disasterFeed.env")


FEED_URI = os.environ.get("FEED_URI") 
print(FEED_URI)
client = BlueskyClient(FEED_URI)
client.login(os.environ.get("BLUESKY_HANDLE"), os.environ.get("BLUESKY_PWD"))

# Initialize AI Model with error handling
def init_model(model_path):
    """Initialize AI model with proper error handling"""
    try:
        logger.info(f"Loading model from {model_path}")

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_path)

        # Define label mappings
        id2label = {
            0: "avalanche", 1: "blizzard", 2: "bush_fire", 3: "cyclone",
            4: "dust_storm", 5: "earthquake", 6: "flood", 7: "forest_fire",
            8: "haze", 9: "hurricane", 10: "landslide", 11: "meteor",
            12: "storm", 13: "tornado", 14: "tsunami", 15: "typhoon",
            16: "unknown", 17: "volcano", 18: "wild_fire"
        }

        # Create the reversed mapping
        label2id = {v: k for k, v in id2label.items()}

        # Create configuration
        config = RobertaConfig.from_pretrained(
            "roberta-base",
            num_labels=19,
            id2label=id2label,
            label2id=label2id
        )

        # Load model
        model = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            config=config,
            ignore_mismatched_sizes=True
        )

        logger.info("Model loaded successfully")
        return tokenizer, model, id2label
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise

aws_config = {
    'region': os.environ.get("AWS_REGION"),
    'key_id': os.environ.get("AWS_ACCESS_KEY_ID"),
    'access_key': os.environ.get("AWS_SECRET_ACCESS_KEY")
}

db = DisasterDatabase(aws_config=aws_config)

def clean_text(text):
    """Clean text by removing URLs, mentions, special chars, etc."""
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    # Remove mentions
    text = re.sub(r'@\w+', '', text)
    # Remove hashtags (keep the text after #)
    text = re.sub(r'#(\w+)', r'\1', text)
    # Remove special characters and numbers
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\d+', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Convert to lowercase
    text = text.lower()
    return text
# Predict disaster type from text
def predict_disaster(tokenizer, model, id2label, text):
    """Predict disaster type from text"""
    try:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        outputs = model(**inputs)
        probabilities = F.softmax(outputs.logits, dim=-1)
        predicted_index = probabilities.argmax().item()
        predicted_label = id2label[predicted_index]
        confidence_score = probabilities[0, predicted_index].item()

        return predicted_label, confidence_score
    except Exception as e:
        logger.error(f"Error predicting disaster: {e}")
        return "unknown", 0.0


if __name__ == "__main__":
    MODEL_PATH = r'/Users/udayvasepalli/Downloads/checkpoint-31710 2'
    tokenizer, model, id2label = init_model(MODEL_PATH)
    client.get_feed()
    for post in client.posts:
        tweet = post['text']
        disaster_type, confidence = predict_disaster(tokenizer, model, id2label, tweet)
        is_disaster = confidence > 0.85
        if is_disaster:
            user_id= db.put_user({
                'user_id': post['author']['did'],
                'handle': post['author']['handle'],
                'display_name': post['author']['display_name'],
                'avatar_url': post['author']['avatar_url']
            })

            post_json = db.put_post({
                'post_id': post['uri'],
                'user_id': post['author']['did'],
                'handle': post['author']['handle'],
                'original_text': post['text'],
                'clean_text': clean_text(post['text']),
                'created_at': post['created_at'],
                'indexed_at': post['indexed_at'],
                'disaster_type': disaster_type,
                'confidence_score': confidence,
                'is_disaster': is_disaster
            })
    
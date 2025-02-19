import torch
from datasets import load_dataset
from transformers import RobertaTokenizerFast, RobertaForSequenceClassification, Trainer, TrainingArguments
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, classification_report
import numpy as np
import random
import os
import logging # Import the logging module
from transformers import EarlyStoppingCallback

# --- Configure basic logging to file ---
logging_dir_full_data = r"F:\AI TRAINING\logs_disaster_type_fulldata_6epoch" # Define logging directory
os.makedirs(logging_dir_full_data, exist_ok=True) # Create directory if it doesn't exist
log_file_path = os.path.join(logging_dir_full_data, "training_logs.log") # Define log file path

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s -   %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(log_file_path),   # Log to file
        logging.StreamHandler()                # Also log to console
    ]
)
logger = logging.getLogger(__name__) # Get logger instance


# 1. Load Dataset
dataset = load_dataset("melisekm/natural-disasters-from-social-media")
train_dataset_full = dataset['train'] # Load the full training dataset
eval_dataset = dataset['validation']

# 2. Analyze Disaster Types and Create Label Mapping (from FULL training and validation sets)
all_event_types_train = train_dataset_full['event_type_detail'] # Get event types from FULL training set
all_event_types_eval = eval_dataset['event_type_detail'] # Get event types from validation set
all_event_types = sorted(list(set(all_event_types_train + all_event_types_eval))) # Combine and get unique types
label2id = {event_type: id for id, event_type in enumerate(all_event_types)}
id2label = {id: event_type for id, event_type in label2id.items()}
num_labels = len(label2id)

logger.info(f"All Unique Disaster Types (from full train + val sets): {all_event_types}") # Log disaster types
logger.info(f"Label to ID Mapping: {label2id}") # Log label mapping
logger.info(f"ID to Label Mapping: {id2label}") # Log ID mapping
logger.info(f"Number of Labels (Disaster Types): {num_labels}") # Log number of labels


# 3. Remove Random Sampling - TRAIN ON FULL DATASET
train_dataset = train_dataset_full # Use the full training dataset directly


# 4. Load Tokenizer and Model (adjust num_labels)
model_name = "roberta-base"
tokenizer = RobertaTokenizerFast.from_pretrained(model_name)
model = RobertaForSequenceClassification.from_pretrained(model_name, num_labels=num_labels, id2label=id2label, label2id=label2id)


# 5. Tokenize and Prepare Dataset (no changes needed to tokenization)
def tokenize_function(examples):
    return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)

tokenized_train_dataset = train_dataset.map(tokenize_function, batched=True)
tokenized_eval_dataset = eval_dataset.map(tokenize_function, batched=True)


# 6. Convert String Labels to Numerical IDs
def encode_labels(examples):
    return {'labels': [label2id[event_type] for event_type in examples['event_type_detail']]}

tokenized_train_dataset = tokenized_train_dataset.map(encode_labels, batched=True)
tokenized_eval_dataset = tokenized_eval_dataset.map(encode_labels, batched=True)


tokenized_train_dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
tokenized_eval_dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])


# 7. Set up Training Arguments (output_dir and logging_dir updated for full dataset, logging_file REMOVED)
output_dir_full_data = r"F:\AI TRAINING\results_disaster_type_roberta_fulldata_6epoch" # Updated output directory for full data
logging_dir_full_data = r"F:\AI TRAINING\logs_disaster_type_fulldata_6epoch" # Updated logging directory for full data


training_args = TrainingArguments(
    output_dir=output_dir_full_data, # Use updated output directory
    num_train_epochs=6,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    learning_rate=2e-5,
    weight_decay=0.01,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1_weighted",
    logging_dir=logging_dir_full_data, # Use updated logging directory
    logging_steps=100,
    report_to="tensorboard" # Keep tensorboard for visualization if you like
)

# 8. Define Evaluation Metrics (using classification_report for more detailed metrics)
def compute_metrics_trainer_multiclass(p):
    predictions, labels = p
    predictions = np.argmax(predictions, axis=1)
    accuracy = accuracy_score(labels, predictions)
    f1_weighted = f1_score(labels, predictions, average='weighted')
    precision_weighted = precision_score(labels, predictions, average='weighted')
    recall_weighted = recall_score(labels, predictions, average='weighted')
    report = classification_report(labels, predictions, target_names=all_event_types, output_dict=True) # Use all_event_types here
    metrics = {
        "accuracy": accuracy,
        "f1_weighted": f1_weighted,
        "precision_weighted": precision_weighted,
        "recall_weighted": recall_weighted,
        "classification_report": report
    }
    return metrics


# 9. Initialize Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train_dataset,
    eval_dataset=tokenized_eval_dataset,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics_trainer_multiclass
)

trainer.add_callback(EarlyStoppingCallback(early_stopping_patience=2))
# 10. Train the Model
trainer.train()

# 11. Evaluate the Fine-tuned Model (on the test set)
test_dataset = dataset['test']
tokenized_test_dataset = test_dataset.map(tokenize_function, batched=True)

def encode_labels_test(examples):
    return {'labels': [label2id.get(event_type, -1) for event_type in examples['event_type_detail']]}

tokenized_test_dataset = tokenized_test_dataset.map(encode_labels_test, batched=True)

# Corrected filtering line:
filtered_test_dataset = tokenized_test_dataset.filter(lambda example: not isinstance(example['labels'], int) and -1 not in example['labels'] if isinstance(example['labels'], list) else example['labels'] != -1)


tokenized_test_dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])


predictions = trainer.predict(tokenized_test_dataset)
predicted_labels = np.argmax(predictions.predictions, axis=1)
true_labels = tokenized_test_dataset['labels']

metrics = compute_metrics_trainer_multiclass((predictions.predictions, true_labels))
logger.info("\nEvaluation Metrics on Test Set (Fine-tuned Model - Disaster Type Classification - Full Data Trained):") # Updated log message
for metric_name, score in metrics.items():
    if metric_name != "classification_report":
        logger.info(f"{metric_name}: {score:.4f}") # Log metrics

logger.info("\nDetailed Classification Report on Test Set (Full Data Trained):") # Updated log message
logger.info(f"\n{metrics['classification_report']}") # Log classification report


# 12. Save Fine-tuned Model and Tokenizer (Updated directory for full dataset)
trainer.save_model(output_dir_full_data) # Save to updated output directory
tokenizer.save_pretrained(output_dir_full_data) # Save to updated output directory

logger.info(f"\nFine-tuning for disaster type classification complete (trained on FULL dataset)! Fine-tuned model and tokenizer saved to '{output_dir_full_data}' directory.") # Updated log message
logger.info(f"Training logs are saved to '{log_file_path}'") # Log file path
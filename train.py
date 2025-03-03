import torch
from torch import nn
from datasets import load_dataset, Dataset
from transformers import RobertaTokenizerFast, RobertaForSequenceClassification, Trainer, TrainingArguments
from transformers import EarlyStoppingCallback
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, classification_report
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from sklearn.model_selection import KFold
import numpy as np
import random
import os
import logging
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from imblearn.over_sampling import RandomOverSampler
import optuna
from optuna.integration import PyTorchLightningPruningCallback
import nlpaug.augmenter.word as naw
import plotly
import matplotlib.colors as colors

# Download NLTK resources
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger_eng')

# --- Configure basic logging to file ---
logging_dir = r"F:\AI TRAINING\logs_disaster_type_fulldata_enhanced_1000samples"
os.makedirs(logging_dir, exist_ok=True)
log_file_path = os.path.join(logging_dir, "training_logs.log")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Output directory setup
output_dir = r"F:\AI TRAINING\results_disaster_type_roberta_enhanced_1000samples"
figures_dir = os.path.join(output_dir, "figures")
os.makedirs(output_dir, exist_ok=True)
os.makedirs(figures_dir, exist_ok=True)


# ============================
# 1. TEXT CLEANING FUNCTIONS
# ============================
def clean_text(text):
    """Clean text by removing URLs, mentions, special chars, etc."""
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    # Remove mentions
    text = re.sub(r'@\w+', '', text)
    # Remove hashtags (keep the text after #)
    text = re.sub(r'#(\w+)', r'\1', text)
    # Remove special characters and numbers
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\d+', ' ', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Convert to lowercase
    text = text.lower()
    return text


def advanced_preprocessing(text, remove_stopwords=False, lemmatize=False):
    """Apply advanced preprocessing options like stopword removal and lemmatization"""
    if remove_stopwords:
        stop_words = set(stopwords.words('english'))
        words = text.split()
        text = ' '.join([word for word in words if word.lower() not in stop_words])

    if lemmatize:
        lemmatizer = WordNetLemmatizer()
        words = text.split()
        text = ' '.join([lemmatizer.lemmatize(word) for word in words])

    return text


# ============================
# 2. DATA ANALYSIS FUNCTIONS
# ============================
def analyze_dataset(dataset, label_col='event_type_detail', text_col='text'):
    """Analyze dataset statistics and create visualizations"""
    logger.info("Starting dataset analysis...")

    # Convert to pandas for easier analysis
    df = pd.DataFrame({
        'text': dataset[text_col],
        'label': dataset[label_col]
    })

    # Add text length
    df['text_length'] = df['text'].apply(len)

    # Class distribution analysis
    class_counts = df['label'].value_counts()
    total_samples = len(df)
    class_distribution = class_counts / total_samples * 100

    # Log basic statistics
    logger.info(f"Total samples: {total_samples}")
    logger.info(f"Number of classes: {len(class_counts)}")
    logger.info(f"Sample count per class:\n{class_counts}")
    logger.info(f"Class distribution (%):\n{class_distribution}")
    logger.info(f"Text length statistics:\n{df['text_length'].describe()}")

    # Visualize class distribution
    plt.figure(figsize=(12, 6))
    plt.bar(range(len(class_counts)), class_counts.values)
    plt.xticks(range(len(class_counts)), class_counts.index, rotation=45, ha='right')
    plt.title('Class Distribution')
    plt.xlabel('Disaster Type')
    plt.ylabel('Number of Samples')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, 'class_distribution.png'))
    plt.close()

    # Visualize text length distribution
    plt.figure(figsize=(10, 6))
    plt.hist(df['text_length'].values, bins=50, alpha=0.7)
    plt.title('Text Length Distribution')
    plt.xlabel('Text Length (characters)')
    plt.ylabel('Frequency')
    plt.axvline(x=df['text_length'].median(), color='r', linestyle='--', label=f'Median: {df["text_length"].median()}')
    plt.axvline(x=128 * 4, color='g', linestyle='--', label='RoBERTa max tokens (~512 chars)')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, 'text_length_distribution.png'))
    plt.close()

    # Text length by class
    plt.figure(figsize=(12, 8))
    labels = class_counts.index.tolist()
    box_data = [df[df['label'] == label]['text_length'].values for label in labels]
    plt.boxplot(box_data, labels=labels)
    plt.title('Text Length by Disaster Type')
    plt.xlabel('Disaster Type')
    plt.ylabel('Text Length (characters)')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, 'text_length_by_class.png'))
    plt.close()

    return df, class_counts


# ============================
# 3. CLASS BALANCING FUNCTIONS
# ============================

def balance_classes(dataset, label_col='labels', strategy='oversample'):
    """Balance classes using specified strategy"""
    # Convert to pandas dataframe
    df = pd.DataFrame({
        'text': dataset['text'],
        'label': dataset[label_col]
    })

    if strategy == 'oversample':
        logger.info("Applying random oversampling to balance classes...")
        oversampler = RandomOverSampler(random_state=42)
        text_array = df['text'].values.reshape(-1, 1)
        labels = df['label'].values

        oversampled_texts, oversampled_labels = oversampler.fit_resample(text_array, labels)

        # Create new balanced dataset
        balanced_dataset = dataset.select(range(0))  # Empty dataset with same structure

        # Add oversampled data
        balanced_dataset = balanced_dataset.add_column('text', oversampled_texts.flatten().tolist())
        balanced_dataset = balanced_dataset.add_column(label_col, oversampled_labels.tolist())

        # Copy other columns if needed
        for col in dataset.column_names:
            if col not in ['text', label_col]:
                # For simplicity, using the first value for all new samples
                # In practice, you'd need to handle this based on your data
                balanced_dataset = balanced_dataset.add_column(col, [dataset[col][0]] * len(oversampled_labels))

        # Visualize before/after
        plt.figure(figsize=(12, 6))
        plt.subplot(1, 2, 1)
        plt.hist(df['label'].values, bins=len(df['label'].unique()))
        plt.title('Before Oversampling')
        plt.xlabel('Class')
        plt.ylabel('Count')

        plt.subplot(1, 2, 2)
        plt.hist(np.array(oversampled_labels), bins=len(np.unique(oversampled_labels)))
        plt.title('After Oversampling')
        plt.xlabel('Class')
        plt.tight_layout()
        plt.savefig(os.path.join(figures_dir, 'class_balancing.png'))
        plt.close()

        return balanced_dataset

    elif strategy == 'class_weights':
        # Calculate class weights inversely proportional to class frequencies
        class_counts = Counter(df['label'])
        n_samples = len(df)
        class_weights = {c: n_samples / (len(class_counts) * count) for c, count in class_counts.items()}
        logger.info(f"Calculated class weights: {class_weights}")
        return dataset, class_weights

    else:
        logger.info("No class balancing applied.")
        return dataset, None


# ============================
# 4. DATA AUGMENTATION FUNCTIONS
# ============================
def augment_text(texts, labels, augmentation_factor=0.3):
    """Augment text data using simple techniques"""
    logger.info(f"Augmenting {len(texts)} samples with factor {augmentation_factor}...")

    # Determine how many samples to augment
    n_to_augment = int(len(texts) * augmentation_factor)
    indices_to_augment = random.sample(range(len(texts)), n_to_augment)

    # Create the augmented dataset (start with original data)
    augmented_texts = list(texts)
    augmented_labels = list(labels)

    # Simple augmentation techniques
    for idx in indices_to_augment:
        text = texts[idx]
        words = text.split()

        if len(words) <= 3:  # Skip very short texts
            continue

        # Pick a random augmentation technique
        technique = random.choice(['swap', 'delete', 'duplicate'])

        if technique == 'swap' and len(words) > 2:
            # Swap two random adjacent words
            swap_idx = random.randint(0, len(words) - 2)
            words[swap_idx], words[swap_idx + 1] = words[swap_idx + 1], words[swap_idx]

        elif technique == 'delete':
            # Delete a random word
            del_idx = random.randint(0, len(words) - 1)
            words.pop(del_idx)

        elif technique == 'duplicate':
            # Duplicate a random word
            dup_idx = random.randint(0, len(words) - 1)
            words.insert(dup_idx, words[dup_idx])

        # Create the augmented text
        augmented_text = ' '.join(words)

        # Add to the dataset
        augmented_texts.append(augmented_text)
        augmented_labels.append(labels[idx])

    logger.info(f"Data augmentation complete. New dataset size: {len(augmented_texts)} (original: {len(texts)})")
    return augmented_texts, augmented_labels


# 10. Define metrics calculation function
def compute_metrics_trainer_multiclass(p):
    predictions, labels = p
    predictions = np.argmax(predictions, axis=1)
    accuracy = accuracy_score(labels, predictions)
    f1_weighted = f1_score(labels, predictions, average='weighted')
    precision_weighted = precision_score(labels, predictions, average='weighted')
    recall_weighted = recall_score(labels, predictions, average='weighted')
    report = classification_report(labels, predictions, target_names=all_event_types, output_dict=True)
    metrics = {
        "accuracy": accuracy,
        "f1_weighted": f1_weighted,
        "precision_weighted": precision_weighted,
        "recall_weighted": recall_weighted,
        "classification_report": report
    }
    return metrics


class WeightedLossTrainer(Trainer):
    def __init__(self, class_weights=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits

        if self.class_weights is not None:
            loss_fct = nn.CrossEntropyLoss(weight=self.class_weights)
        else:
            loss_fct = nn.CrossEntropyLoss()

        loss = loss_fct(logits.view(-1, self.model.config.num_labels), labels.view(-1))

        return (loss, outputs) if return_outputs else loss

# ============================
# 5. HYPERPARAMETER OPTIMIZATION
# ============================
def objective(trial, train_dataset, eval_dataset, tokenizer, num_labels, id2label, label2id, class_weights_tensor=None):
    """Objective function for hyperparameter optimization"""
    # Hyperparameters to optimize
    learning_rate = trial.suggest_float("learning_rate", 1e-6, 1e-4, log=True)
    batch_size = trial.suggest_categorical("batch_size", [8, 16, 32])
    weight_decay = trial.suggest_float("weight_decay", 0.001, 0.1, log=True)

    # Model initialization
    model = RobertaForSequenceClassification.from_pretrained(
        "roberta-base",
        num_labels=num_labels,
        id2label=id2label,
        label2id=label2id
    )

    # Training arguments
    training_args = TrainingArguments(
        output_dir=os.path.join(output_dir, f"trial_{trial.number}"),
        num_train_epochs=3,  # Use fewer epochs for HPO
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1_weighted",
        logging_dir=os.path.join(logging_dir, f"trial_{trial.number}"),
        logging_steps=100,
        report_to="none",  # Disable reporting during HPO
    )

    # Initialize trainer
    trainer = WeightedLossTrainer(
        class_weights=class_weights_tensor,
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics_trainer_multiclass
    )

    # Train and evaluate
    trainer.train()
    eval_result = trainer.evaluate()

    return eval_result["eval_f1_weighted"]


def run_hyperparameter_optimization(train_dataset, eval_dataset, tokenizer, num_labels, id2label, label2id,
                                   class_weights_tensor=None, n_trials=10):
    """Run hyperparameter optimization using Optuna"""
    logger.info(f"Starting hyperparameter optimization with {n_trials} trials...")

    study = optuna.create_study(direction="maximize")
    study.optimize(
        lambda trial: objective(
            trial, train_dataset, eval_dataset, tokenizer, num_labels, id2label, label2id, class_weights_tensor
        ),
        n_trials=n_trials
    )

    logger.info(f"Best trial: {study.best_trial.number}")
    logger.info(f"Best F1 score: {study.best_trial.value:.4f}")
    logger.info(f"Best hyperparameters: {study.best_trial.params}")

    # Visualize optimization results
    try:
        fig = optuna.visualization.plot_optimization_history(study)
        if hasattr(fig, 'write_image'):
            fig.write_image(os.path.join(figures_dir, 'optuna_history.png'))

        fig = optuna.visualization.plot_param_importances(study)
        if hasattr(fig, 'write_image'):
            fig.write_image(os.path.join(figures_dir, 'optuna_param_importance.png'))
    except ImportError:
        logger.warning("Plotly is not installed. Skipping Optuna visualization.")

    return study.best_trial.params


# ============================
# 6. PERFORMANCE VISUALIZATION
# ============================
def plot_confusion_matrix(y_true, y_pred, labels):
    """Plot and save confusion matrix with improved readability"""
    # Create the confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=range(len(labels)))

    # Create a larger figure for better readability
    plt.figure(figsize=(24, 20))  # Significantly larger than before

    # Use abbreviated class names if they're too long
    display_labels = [label[:20] + '...' if len(label) > 20 else label for label in labels]

    # Create the confusion matrix display
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=display_labels)

    # Plot with more customization
    disp.plot(
        cmap='Blues',
        xticks_rotation=90,
        values_format='.0f',  # Show integers only
        ax=plt.gca()
    )

    # Add title with larger font
    plt.title('Confusion Matrix', fontsize=24, pad=20)

    # Adjust labels with larger fonts
    plt.xlabel('Predicted label', fontsize=18)
    plt.ylabel('True label', fontsize=18)

    # Improve spacing
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15, left=0.15)

    # Optionally hide small values to reduce visual clutter
    ax = plt.gca()
    threshold = 10  # Only show values above this threshold

    # Find total number of texts in the plot
    text_count = len(labels) * len(labels)

    # Hide small values if there are texts to modify
    if len(ax.texts) == text_count:
        for i in range(len(labels)):
            for j in range(len(labels)):
                # Only show values above threshold
                if cm[i, j] < threshold:
                    # Find the corresponding text element and hide it
                    text_idx = i * len(labels) + j
                    if text_idx < len(ax.texts):
                        ax.texts[text_idx].set_visible(False)

    # Save the figure with high resolution
    plt.savefig(os.path.join(figures_dir, 'confusion_matrix.png'), dpi=150, bbox_inches='tight')
    plt.close()

    # Create a second version with logarithmic scale for better visualization
    plt.figure(figsize=(24, 20))

    # Add a small value to avoid log(0)
    cm_log = cm.copy() + 1

    # Create the log-scale display
    disp = ConfusionMatrixDisplay(confusion_matrix=cm_log, display_labels=display_labels)

    # Plot with log normalization - using a different approach
    fig, ax = plt.subplots(figsize=(24, 20))

    # Manually create the plot with LogNorm
    import matplotlib.colors as colors
    im = ax.imshow(cm_log, cmap='Blues', norm=colors.LogNorm(vmin=1, vmax=cm_log.max()))

    # Add color bar
    plt.colorbar(im, ax=ax)

    # Add tick labels
    ax.set_xticks(np.arange(len(display_labels)))
    ax.set_yticks(np.arange(len(display_labels)))
    ax.set_xticklabels(display_labels, rotation=90)
    ax.set_yticklabels(display_labels)

    # Loop over data dimensions and create text annotations
    thresh = cm_log.max() / 2.
    for i in range(len(display_labels)):
        for j in range(len(display_labels)):
            if cm_log[i, j] > threshold:  # Only show values above threshold
                ax.text(j, i, format(cm_log[i, j] - 1, '.0f'),
                        ha="center", va="center",
                        color="white" if cm_log[i, j] > thresh else "black")

    plt.title('Confusion Matrix (Log Scale)', fontsize=24, pad=20)
    plt.xlabel('Predicted label', fontsize=18)
    plt.ylabel('True label', fontsize=18)
    plt.tight_layout()

    # Save the log-scale version too
    plt.savefig(os.path.join(figures_dir, 'confusion_matrix_log_scale.png'), dpi=150, bbox_inches='tight')
    plt.close()


def plot_training_history(trainer):
    """Plot training history from trainer logs with improved validation display"""
    log_history = trainer.state.log_history

    # Extract training and evaluation metrics
    train_loss = []
    train_steps = []
    eval_loss = []
    eval_steps = []
    eval_f1 = []

    # Process the log history
    for entry in log_history:
        if 'loss' in entry and 'step' in entry and 'eval_loss' not in entry:
            train_loss.append(entry['loss'])
            train_steps.append(entry['step'])
        elif 'eval_loss' in entry and 'step' in entry:
            eval_loss.append(entry['eval_loss'])
            eval_steps.append(entry['step'])
            if 'eval_f1_weighted' in entry:
                eval_f1.append(entry['eval_f1_weighted'])

    # Plot training and evaluation loss
    plt.figure(figsize=(12, 6))

    # Add training loss curve
    plt.plot(train_steps, train_loss, 'b-', label='Training Loss', alpha=0.7)

    # Add validation loss points with clear markers and connecting lines
    if eval_steps:
        plt.plot(eval_steps, eval_loss, 'ro-', label='Validation Loss',
                 markersize=8, linewidth=2)

    plt.title('Training and Validation Loss', fontsize=16)
    plt.xlabel('Steps', fontsize=14)
    plt.ylabel('Loss', fontsize=14)
    plt.legend(fontsize=12)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(figures_dir, 'training_validation_loss.png'))
    plt.close()

    # Plot F1 score progression if available
    if eval_f1:
        plt.figure(figsize=(10, 5))
        epochs = range(1, len(eval_f1) + 1)
        plt.plot(epochs, eval_f1, 'bo-', label='F1 Weighted', markersize=8)
        plt.title('F1 Score Progression', fontsize=16)
        plt.xlabel('Epochs', fontsize=14)
        plt.ylabel('F1 Score', fontsize=14)
        plt.grid(True)
        plt.legend(fontsize=12)
        plt.tight_layout()
        plt.savefig(os.path.join(figures_dir, 'f1_progression.png'))
        plt.close()


# ============================
# MAIN PROCESSING PIPELINE
# ============================
# 1. Load Dataset
logger.info("Loading dataset...")
dataset = load_dataset("melisekm/natural-disasters-from-social-media")

# Limit training dataset to 1000 samples while maintaining class distribution
train_dataset_full = dataset['train']
logger.info(f"Original training dataset size: {len(train_dataset_full)}")


# Function to sample dataset while preserving class distribution
def sample_stratified(dataset, num_samples=1000):
    # Get class distribution
    labels = dataset['event_type_detail']
    unique_labels = set(labels)

    # Calculate how many samples per class
    label_counts = {label: labels.count(label) for label in unique_labels}
    total = len(labels)

    # Calculate target counts per class
    target_counts = {label: max(1, int(count / total * num_samples)) for label, count in label_counts.items()}

    # Adjust to ensure we get exactly num_samples
    adjustment = num_samples - sum(target_counts.values())
    if adjustment != 0:
        # Sort labels by frequency for adjustment
        sorted_labels = sorted(label_counts.keys(), key=lambda l: label_counts[l], reverse=True)
        for i in range(abs(adjustment)):
            label = sorted_labels[i % len(sorted_labels)]
            target_counts[label] += 1 if adjustment > 0 else -1
            # Ensure no negative counts
            target_counts[label] = max(1, target_counts[label])

    # Sample from each class
    indices = []
    for label, count in target_counts.items():
        label_indices = [i for i, l in enumerate(labels) if l == label]
        # If we need more than available, sample with replacement
        if count > len(label_indices):
            sampled = random.choices(label_indices, k=count)
        else:
            sampled = random.sample(label_indices, count)
        indices.extend(sampled)

    # Double-check we have the right number
    if len(indices) != num_samples:
        # Adjust by randomly adding or removing indices
        if len(indices) < num_samples:
            additional = random.sample(range(len(dataset)), num_samples - len(indices))
            indices.extend(additional)
        else:
            indices = random.sample(indices, num_samples)

    return dataset.select(indices)


# Sample the training dataset
train_dataset_full = sample_stratified(train_dataset_full, num_samples=1000)
eval_dataset = dataset['validation']
test_dataset = dataset['test']

logger.info(f"Sampled training dataset size: {len(train_dataset_full)}")
logger.info(f"Class distribution in sampled dataset: {Counter(train_dataset_full['event_type_detail'])}")


## Use this to pull all dataset
#logger.info("Loading dataset...")
#dataset = load_dataset("melisekm/natural-disasters-from-social-media")
#train_dataset_full = dataset['train']
#eval_dataset = dataset['validation']
#test_dataset = dataset['test']

# 2. Data Analysis
logger.info("Performing data analysis...")
train_df, class_counts = analyze_dataset(train_dataset_full)

# 3. Text Cleaning and Preprocessing
logger.info("Applying text cleaning...")


def preprocess_dataset(dataset):
    # Clean text
    cleaned_texts = [clean_text(text) for text in dataset['text']]
    # Apply advanced preprocessing
    processed_texts = [advanced_preprocessing(text, remove_stopwords=False, lemmatize=True) for text in cleaned_texts]

    # Update dataset with cleaned texts
    # Create a new dataset with the same structure
    processed_dataset = dataset.select(range(len(dataset)))
    # Remove the original text column
    processed_dataset = processed_dataset.remove_columns(['text'])
    # Add the processed text column
    processed_dataset = processed_dataset.add_column('text', processed_texts)

    return processed_dataset


train_dataset_full = preprocess_dataset(train_dataset_full)
eval_dataset = preprocess_dataset(eval_dataset)
test_dataset = preprocess_dataset(test_dataset)

# 4. Label Mapping Creation
all_event_types_train = train_dataset_full['event_type_detail']
all_event_types_eval = eval_dataset['event_type_detail']
all_event_types = sorted(list(set(all_event_types_train + all_event_types_eval)))
label2id = {event_type: id for id, event_type in enumerate(all_event_types)}
id2label = {id: event_type for id, event_type in label2id.items()}
num_labels = len(label2id)

logger.info(f"All Unique Disaster Types: {all_event_types}")
logger.info(f"Number of Labels: {num_labels}")

# 5. Class Balancing
train_dataset, class_weights = balance_classes(train_dataset_full, label_col='event_type_detail',
                                              strategy='class_weights')

# Convert class weights to tensor early
if class_weights:
    weight_values = []
    for i in range(num_labels):
        weight_values.append(class_weights.get(i, 1.0))
    class_weights_tensor = torch.tensor(weight_values, dtype=torch.float).to('cuda' if torch.cuda.is_available() else 'cpu')
else:
    class_weights_tensor = None

# 6. Data Augmentation
augmented_texts, augmented_labels = augment_text(train_dataset['text'], train_dataset['event_type_detail'])

# Create augmented dataset
train_dataset_augmented = Dataset.from_dict({
    'text': augmented_texts,
    'event_type_detail': augmented_labels
})

# 7. Tokenize and Prepare Dataset
model_name = "roberta-base"
tokenizer = RobertaTokenizerFast.from_pretrained(model_name)


def tokenize_function(examples):
    return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)


tokenized_train_dataset = train_dataset_augmented.map(tokenize_function, batched=True)
tokenized_eval_dataset = eval_dataset.map(tokenize_function, batched=True)


# 8. Convert String Labels to Numerical IDs
def encode_labels(examples):
    return {'labels': [label2id[event_type] for event_type in examples['event_type_detail']]}


tokenized_train_dataset = tokenized_train_dataset.map(encode_labels, batched=True)
tokenized_eval_dataset = tokenized_eval_dataset.map(encode_labels, batched=True)

tokenized_train_dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
tokenized_eval_dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

# 9. Hyperparameter Optimization (if enabled)
run_hpo = True  # Set to False to skip hyperparameter optimization
if run_hpo:
    best_params = run_hyperparameter_optimization(
        tokenized_train_dataset,
        tokenized_eval_dataset,
        tokenizer,
        num_labels,
        id2label,
        label2id,
        class_weights_tensor=class_weights_tensor,
        n_trials=5
    )
    learning_rate = best_params['learning_rate']
    batch_size = best_params['batch_size']
    weight_decay = best_params['weight_decay']
else:
    # Default hyperparameters
    learning_rate = 2e-5
    batch_size = 16
    weight_decay = 0.01





# 11. Configure Training Arguments
training_args = TrainingArguments(
    output_dir=output_dir,
    num_train_epochs=6,
    per_device_train_batch_size=batch_size,
    per_device_eval_batch_size=batch_size,
    learning_rate=learning_rate,
    weight_decay=weight_decay,
    evaluation_strategy="steps",
    eval_steps=100,
    save_strategy="steps",
    save_steps=100,
    load_best_model_at_end=True,
    metric_for_best_model="f1_weighted",
    logging_dir=logging_dir,
    logging_steps=20,
    report_to="tensorboard",
)




# 12. Initialize and Train the Model
model = RobertaForSequenceClassification.from_pretrained(
    model_name,
    num_labels=num_labels,
    id2label=id2label,
    label2id=label2id
)

trainer = WeightedLossTrainer(
    class_weights=class_weights_tensor,
    model=model,
    args=training_args,
    train_dataset=tokenized_train_dataset,
    eval_dataset=tokenized_eval_dataset,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics_trainer_multiclass
)

trainer.add_callback(EarlyStoppingCallback(early_stopping_patience=2))

# 13. Train the Model
logger.info("Starting model training...")
trainer.train()

# 14. Plot training history
plot_training_history(trainer)

# 15. Evaluate on the Test Set
tokenized_test_dataset = test_dataset.map(tokenize_function, batched=True)


def encode_labels_test(examples):
    return {'labels': [label2id.get(event_type, -1) for event_type in examples['event_type_detail']]}


tokenized_test_dataset = tokenized_test_dataset.map(encode_labels_test, batched=True)
filtered_test_dataset = tokenized_test_dataset.filter(
    lambda example: not isinstance(example['labels'], int) and -1 not in example['labels']
    if isinstance(example['labels'], list) else example['labels'] != -1
)
tokenized_test_dataset.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

predictions = trainer.predict(tokenized_test_dataset)
predicted_labels = np.argmax(predictions.predictions, axis=1)
true_labels = tokenized_test_dataset['labels']

# 16. Compute and Log Metrics
metrics = compute_metrics_trainer_multiclass((predictions.predictions, true_labels))
logger.info("\nEvaluation Metrics on Test Set:")
for metric_name, score in metrics.items():
    if metric_name != "classification_report":
        logger.info(f"{metric_name}: {score:.4f}")

logger.info("\nDetailed Classification Report on Test Set:")
logger.info(f"\n{metrics['classification_report']}")

# 17. Plot Confusion Matrix
plot_confusion_matrix(true_labels, predicted_labels, all_event_types)

# 18. Save Fine-tuned Model and Tokenizer
trainer.save_model(output_dir)
tokenizer.save_pretrained(output_dir)

logger.info(f"\nEnhanced training complete! Fine-tuned model and tokenizer saved to '{output_dir}'.")
logger.info(f"Training logs are saved to '{log_file_path}'")
logger.info(f"Visualizations are saved in '{figures_dir}'")
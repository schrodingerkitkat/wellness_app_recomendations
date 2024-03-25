import pandas as pd
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score, precision_score, recall_score, f1_score
from sklearn.pipeline import Pipeline
import joblib
import boto3

# Load the SpaCy English model
nlp = spacy.load("en_core_web_sm")

def preprocess_text(text):
    """Preprocess text by removing stopwords and lemmatizing."""
    doc = nlp(text)
    cleaned_text = " ".join(token.lemma_.lower() for token in doc if token.text.lower() not in STOP_WORDS and not token.is_punct)
    return cleaned_text

def sentiment_analysis(df, text_column):
    """
    Perform sentiment analysis on user feedback.
    
    Args:
    - df: DataFrame containing the text data.
    - text_column: The name of the column containing the text.
    """
    # Preprocess the text data
    df["cleaned_text"] = df[text_column].apply(preprocess_text)

    # Feature extraction using TF-IDF
    vectorizer = TfidfVectorizer(max_features=1000)
    X = vectorizer.fit_transform(df["cleaned_text"])
    y = df["sentiment"]

    # Splitting the dataset into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

    # Model training with hyperparameter tuning using GridSearchCV
    pipeline = Pipeline([
        ('classifier', LogisticRegression())
    ])

    parameters = {
        'classifier__C': [0.1, 1, 10],
        'classifier__penalty': ['l1', 'l2']
    }

    grid_search = GridSearchCV(pipeline, parameters, cv=5, scoring='accuracy')
    grid_search.fit(X_train, y_train)

    # Model evaluation
    best_model = grid_search.best_estimator_
    y_pred = best_model.predict(X_test)

    print("Best Model Parameters:", grid_search.best_params_)
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("Precision:", precision_score(y_test, y_pred, average='weighted'))
    print("Recall:", recall_score(y_test, y_pred, average='weighted'))
    print("F1 Score:", f1_score(y_test, y_pred, average='weighted'))
    print("Classification Report:\n", classification_report(y_test, y_pred))

    # Save the trained model and vectorizer
    joblib.dump(best_model, 'sentiment_analysis_model.pkl')
    joblib.dump(vectorizer, 'tfidf_vectorizer.pkl')

def load_data_from_s3(bucket_name, file_name):
    """Load data from a gold S3 bucket."""
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=bucket_name, Key=file_name)
    df = pd.read_csv(obj['Body'])
    return df

# Main execution
if __name__ == "__main__":
    bucket_name = "gold-bucket"
    file_name = "user_feedback.csv"
    df = load_data_from_s3(bucket_name, file_name)
    sentiment_analysis(df, "feedback_text")

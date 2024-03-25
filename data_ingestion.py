import hashlib
import pandas as pd
from google.cloud import bigquery
from sqlalchemy import create_engine
from datetime import datetime

def generate_hash_key(values):
    return hashlib.sha256(''.join(map(str, values)).encode()).hexdigest()

def ingest_to_bigquery(dataframe, dataset_id, table_id, bq_client):
    table_ref = f"{bq_client.project}.{dataset_id}.{table_id}"
    job_config = bigquery.LoadJobConfig(
        autodetect=True,
        write_disposition="WRITE_APPEND",
    )
    job = bq_client.load_table_from_dataframe(dataframe, table_ref, job_config=job_config)
    job.result()  # Wait for the job to complete

def ingest_to_redshift(dataframe, table_name, redshift_engine):
    dataframe['ingestion_timestamp'] = datetime.now()
    dataframe.to_sql(table_name, redshift_engine, if_exists='append', index=False)

def preprocess_data(dataframe):
    # Perform data preprocessing and cleansing
    dataframe = dataframe.dropna()
    dataframe = dataframe.drop_duplicates()
    # more steps to come
    return dataframe

def main():
    bq_client = bigquery.Client()
    redshift_engine = create_engine('postgresql+psycopg2://user:password@host:port/dbname')

    # Load data from various sources
    user_data = pd.read_csv('path/to/user_data.csv')
    interaction_data = pd.read_json('path/to/interaction_data.json')
    content_data = pd.read_parquet('path/to/content_data.parquet')

    # Preprocess and cleanse the data
    user_data = preprocess_data(user_data)
    interaction_data = preprocess_data(interaction_data)
    content_data = preprocess_data(content_data)

    # Generate hash keys for entity matching
    user_data['user_hash_key'] = user_data.apply(lambda row: generate_hash_key([row['user_id']]), axis=1)
    interaction_data['interaction_hash_key'] = interaction_data.apply(lambda row: generate_hash_key([row['user_id'], row['interaction_time']]), axis=1)
    content_data['content_hash_key'] = content_data.apply(lambda row: generate_hash_key([row['content_id']]), axis=1)

    # Ingest data into BigQuery
    ingest_to_bigquery(user_data, 'user_dataset', 'user_table', bq_client)
    ingest_to_bigquery(interaction_data, 'interaction_dataset', 'interaction_table', bq_client)
    ingest_to_bigquery(content_data, 'content_dataset', 'content_table', bq_client)

    # Ingest data into Redshift
    ingest_to_redshift(user_data, 'user_table', redshift_engine)
    ingest_to_redshift(interaction_data, 'interaction_table', redshift_engine)
    ingest_to_redshift(content_data, 'content_table', redshift_engine)

if __name__ == "__main__":
    main()

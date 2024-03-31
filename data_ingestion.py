import hashlib
import pandas as pd
from google.cloud import bigquery
from sqlalchemy import create_engine
from datetime import datetime
import boto3
import io

def generate_hash_key(values):
    return hashlib.sha256(''.join(map(str, values)).encode()).hexdigest()

def ingest_to_bigquery(dataframe, dataset_id, table_id, bq_client):
    table_ref = f"{bq_client.project}.{dataset_id}.{table_id}"
    job_config = bigquery.LoadJobConfig(
        autodetect=True,
        write_disposition="WRITE_APPEND",
    )
    job = bq_client.load_table_from_dataframe(dataframe, table_ref, job_config=job_config)
    job.result()

def ingest_to_redshift(dataframe, table_name, redshift_engine):
    dataframe['ingestion_timestamp'] = datetime.now()
    dataframe.to_sql(table_name, redshift_engine, if_exists='append', index=False)

def preprocess_data(dataframe):
    dataframe = dataframe.dropna()
    dataframe = dataframe.drop_duplicates()
    return dataframe

def load_from_s3(s3_bucket, s3_key, aws_access_key_id, aws_secret_access_key):
    s3_client = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    return pd.read_parquet(io.BytesIO(response['Body'].read()))

def main():
    bq_client = bigquery.Client()
    redshift_engine = create_engine('postgresql+psycopg2://user:password@host:port/dbname')
    
    # Load data from gold S3 buckets
    user_data = load_from_s3('user-gold-bucket', 'user_data.parquet', 'aws_access_key_id', 'aws_secret_access_key')
    interaction_data = load_from_s3('interaction-gold-bucket', 'interaction_data.parquet', 'aws_access_key_id', 'aws_secret_access_key')
    content_data = load_from_s3('content-gold-bucket', 'content_data.parquet', 'aws_access_key_id', 'aws_secret_access_key')
    
    # Preprocess and cleanse the data
    user_data = preprocess_data(user_data)
    interaction_data = preprocess_data(interaction_data)
    content_data = preprocess_data(content_data)
    
    # Generate hash keys for data vault modeling
    user_data['user_hash_key'] = user_data.apply(lambda row: generate_hash_key([row['user_id']]), axis=1)
    interaction_data['interaction_hash_key'] = interaction_data.apply(lambda row: generate_hash_key([row['user_id'], row['interaction_time']]), axis=1)
    content_data['content_hash_key'] = content_data.apply(lambda row: generate_hash_key([row['content_id']]), axis=1)
    
    # Ingest data into BigQuery
    ingest_to_bigquery(user_data, 'user_dataset', 'user_hub', bq_client)
    ingest_to_bigquery(interaction_data, 'interaction_dataset', 'interaction_link', bq_client)
    ingest_to_bigquery(content_data, 'content_dataset', 'content_hub', bq_client)
    
    # Ingest data into Redshift
    ingest_to_redshift(user_data, 'user_hub', redshift_engine)
    ingest_to_redshift(interaction_data, 'interaction_link', redshift_engine)
    ingest_to_redshift(content_data, 'content_hub', redshift_engine)

if __name__ == "__main__":
    main()
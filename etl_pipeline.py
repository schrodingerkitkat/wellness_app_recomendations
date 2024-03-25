from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, sha2, concat_ws
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType

def create_spark_session():
    return SparkSession.builder \
        .appName("Mental Health Recommendation ETL") \
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic") \
        .getOrCreate()

def load_data(spark, data_path, schema):
    return spark.read \
        .schema(schema) \
        .json(data_path)

def transform_interactions(df_interactions):
    return df_interactions \
        .withColumn("interaction_hashkey", sha2(concat_ws("", col("user_id"), col("interaction_time")), 256)) \
        .withColumn("load_date", current_timestamp())

def transform_users(df_users):
    return df_users \
        .withColumn("user_hashkey", sha2(col("user_id"), 256)) \
        .withColumn("load_date", current_timestamp())

def write_to_gold(dataframe, output_path):
    dataframe.write \
        .mode("overwrite") \
        .partitionBy("load_date") \
        .parquet(output_path)

def sync_to_bigquery(spark, dataframe, dataset_name, table_name):
    dataframe.write \
        .format("bigquery") \
        .option("temporaryGcsBucket", "your-gcs-bucket") \
        .mode("append") \
        .save(f"{dataset_name}.{table_name}")

def sync_to_redshift(spark, dataframe, table_name, redshift_jdbc_url):
    dataframe.write \
        .format("jdbc") \
        .option("url", redshift_jdbc_url) \
        .option("dbtable", table_name) \
        .mode("append") \
        .save()

def etl_process():
    spark = create_spark_session()

    # Define schema for interaction data
    interaction_schema = StructType([
        StructField("user_id", StringType(), True),
        StructField("interaction_time", TimestampType(), True),
        # more fields to come
    ])

    # Define schema for user data
    user_schema = StructType([
        StructField("user_id", StringType(), True),
        StructField("email", StringType(), True),
        StructField("age", IntegerType(), True),
        # more fields to come
    ])

    # Load data
    df_interactions = load_data(spark, "s3a://path/to/interactions", interaction_schema)
    df_users = load_data(spark, "s3a://path/to/users", user_schema)

    # Perform transformations
    df_interactions_transformed = transform_interactions(df_interactions)
    df_users_transformed = transform_users(df_users)

    # Write to Gold layer in S3
    write_to_gold(df_interactions_transformed, "s3a://path/to/gold/interactions")
    write_to_gold(df_users_transformed, "s3a://path/to/gold/users")

    # Sync to BigQuery
    sync_to_bigquery(spark, df_interactions_transformed, "dataset", "interactions")
    sync_to_bigquery(spark, df_users_transformed, "dataset", "users")

    # Sync to Redshift
    redshift_jdbc_url = "jdbc:redshift://redshift-endpoint:5439/your-database"
    sync_to_redshift(spark, df_interactions_transformed, "interactions", redshift_jdbc_url)
    sync_to_redshift(spark, df_users_transformed, "users", redshift_jdbc_url)

if __name__ == "__main__":
    etl_process()

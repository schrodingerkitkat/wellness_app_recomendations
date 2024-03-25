from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, lit
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType

def create_spark_session():
    return SparkSession.builder \
        .appName("Data Validation") \
        .getOrCreate()

def validate_schema(dataframe, expected_schema):
    if dataframe.schema != expected_schema:
        raise ValueError("Data validation failed: Schema mismatch")

def validate_missing_values(dataframe, columns):
    for column in columns:
        missing_count = dataframe.filter(col(column).isNull()).count()
        if missing_count > 0:
            raise ValueError(f"Data validation failed: Missing values in column '{column}'")

def validate_duplicates(dataframe, key_columns):
    duplicate_count = dataframe.groupBy(key_columns).agg(count("*").alias("count")).filter(col("count") > 1).count()
    if duplicate_count > 0:
        raise ValueError(f"Data validation failed: Duplicate records found based on key columns {key_columns}")

def validate_data_range(dataframe, column, min_value, max_value):
    invalid_count = dataframe.filter((col(column) < min_value) | (col(column) > max_value)).count()
    if invalid_count > 0:
        raise ValueError(f"Data validation failed: Values in column '{column}' are outside the valid range")

def validate_data():
    spark = create_spark_session()

    # Define expected schemas
    interaction_schema = StructType([
        StructField("user_id", StringType(), True),
        StructField("interaction_time", TimestampType(), True),
        # more to come
    ])

    user_schema = StructType([
        StructField("user_id", StringType(), True),
        StructField("email", StringType(), True),
        StructField("age", IntegerType(), True),
        # more fields to come
    ])

    # Read data from Gold layer
    df_interactions = spark.read.parquet("s3a://path/to/gold/interactions")
    df_users = spark.read.parquet("s3a://path/to/gold/users")

    # Validate schema
    validate_schema(df_interactions, interaction_schema)
    validate_schema(df_users, user_schema)

    # Validate missing values
    validate_missing_values(df_interactions, ["user_id", "interaction_time"])
    validate_missing_values(df_users, ["user_id", "email"])

    # Validate duplicates
    validate_duplicates(df_interactions, ["user_id", "interaction_time"])
    validate_duplicates(df_users, ["user_id"])

    # Validate data range
    validate_data_range(df_users, "age", 18, 100)

    print("Data validation completed successfully!")

if __name__ == "__main__":
    validate_data()

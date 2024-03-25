from pyspark.sql import SparkSession
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator
from pyspark.sql.functions import col

def create_spark_session():
    return SparkSession.builder \
        .appName("RecommendationEngine") \
        .config("spark.sql.crossJoin.enabled", "true") \
        .getOrCreate()

def preprocess_data(data):
    """Preprocess the data."""
    # data preprocessing steps
    # First: Convert rating to float and select relevant columns
    return data.withColumn("rating", col("rating").cast("float")) \
        .select("userId", "contentId", "rating")

def train_model(data):
    """Train a collaborative filtering model."""
    als = ALS(maxIter=5, regParam=0.01, userCol="userId", itemCol="contentId", ratingCol="rating")
    model = als.fit(data)
    return model

def evaluate_model(model, test_data):
    """Evaluate the model's performance."""
    predictions = model.transform(test_data)
    evaluator = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")
    rmse = evaluator.evaluate(predictions)
    print(f"Root-mean-square error = {rmse}")

def tune_hyperparameters(data):
    """Perform hyperparameter tuning."""
    als = ALS(userCol="userId", itemCol="contentId", ratingCol="rating")
    param_grid = ParamGridBuilder() \
        .addGrid(als.maxIter, [5, 10, 15]) \
        .addGrid(als.regParam, [0.01, 0.1, 1.0]) \
        .build()
    evaluator = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")
    cv = CrossValidator(estimator=als, estimatorParamMaps=param_grid, evaluator=evaluator, numFolds=3)
    cv_model = cv.fit(data)
    return cv_model.bestModel

def main():
    spark = create_spark_session()

    # paths to the pre-processed datasets
    data_path = "s3://gold-bucket/training_data.csv"
    test_data_path = "s3://gold-bucket/test_data.csv"

    # Read and preprocess the data
    data = spark.read.csv(data_path, header=True, inferSchema=True)
    data = preprocess_data(data)
    test_data = spark.read.csv(test_data_path, header=True, inferSchema=True)
    test_data = preprocess_data(test_data)

    # Train the model
    model = train_model(data)

    # Evaluate the model
    evaluate_model(model, test_data)

    # Perform hyperparameter tuning
    best_model = tune_hyperparameters(data)

    # Evaluate the best model
    evaluate_model(best_model, test_data)

if __name__ == "__main__":
    main()

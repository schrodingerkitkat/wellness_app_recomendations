from pyspark.sql import SparkSession
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.sql.functions import col
import mlflow
import mlflow.spark
from typing import Dict, Any
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_spark_session():
    """Create optimized Spark session for model training"""
    return SparkSession.builder \
        .appName("RecommendationEngine-Optimized") \
        .config("spark.sql.crossJoin.enabled", "true") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .getOrCreate()

def preprocess_data(data):
    """Preprocess and cache data for faster access"""
    processed_data = data.withColumn("rating", col("rating").cast("float")) \
        .select("userId", "contentId", "rating") \
        .filter(col("rating").isNotNull()) \
        .cache()  # Cache for reuse in hyperparameter tuning
    
    logger.info(f"Processed {processed_data.count()} records")
    return processed_data

def fast_hyperparameter_search(train_data, validation_data) -> Dict[str, Any]:
    """Optimized hyperparameter search using train-validation split"""
    
    # Reduced parameter grid for faster search
    param_combinations = [
        {"maxIter": 10, "regParam": 0.01, "rank": 10},
        {"maxIter": 10, "regParam": 0.1, "rank": 10},
        {"maxIter": 15, "regParam": 0.01, "rank": 20},
        {"maxIter": 15, "regParam": 0.1, "rank": 20}
    ]
    
    evaluator = RegressionEvaluator(
        metricName="rmse", 
        labelCol="rating", 
        predictionCol="prediction"
    )
    
    best_params = None
    best_rmse = float('inf')
    best_model = None
    
    for params in param_combinations:
        start_time = time.time()
        
        als = ALS(
            userCol="userId", 
            itemCol="contentId", 
            ratingCol="rating",
            coldStartStrategy="drop",  # Handle cold start problem
            **params
        )
        
        model = als.fit(train_data)
        predictions = model.transform(validation_data)
        rmse = evaluator.evaluate(predictions)
        
        training_time = time.time() - start_time
        
        logger.info(f"Params: {params}, RMSE: {rmse:.4f}, Time: {training_time:.2f}s")
        
        # Log to MLflow
        with mlflow.start_run(nested=True):
            mlflow.log_params(params)
            mlflow.log_metric("rmse", rmse)
            mlflow.log_metric("training_time", training_time)
        
        if rmse < best_rmse:
            best_rmse = rmse
            best_params = params
            best_model = model
    
    logger.info(f"Best params: {best_params}, Best RMSE: {best_rmse:.4f}")
    return best_model, best_params, best_rmse

def evaluate_model_performance(model, test_data) -> Dict[str, float]:
    """Comprehensive model evaluation"""
    start_time = time.time()
    
    predictions = model.transform(test_data)
    evaluator = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")
    
    rmse = evaluator.evaluate(predictions)
    mae_evaluator = RegressionEvaluator(metricName="mae", labelCol="rating", predictionCol="prediction")
    mae = mae_evaluator.evaluate(predictions)
    
    inference_time = time.time() - start_time
    
    metrics = {
        "rmse": rmse,
        "mae": mae,
        "inference_time": inference_time,
        "test_records": test_data.count()
    }
    
    logger.info(f"Model evaluation: {metrics}")
    return metrics

def main():
    # Initialize MLflow
    mlflow.set_experiment("wellness-recommendation-engine")
    
    spark = create_spark_session()
    
    try:
        with mlflow.start_run():
            # Load data
            data_path = "s3://gold-bucket/training_data.csv"
            test_data_path = "s3://gold-bucket/test_data.csv"
            
            logger.info("Loading training data...")
            data = spark.read.csv(data_path, header=True, inferSchema=True)
            data = preprocess_data(data)
            
            logger.info("Loading test data...")
            test_data = spark.read.csv(test_data_path, header=True, inferSchema=True)
            test_data = preprocess_data(test_data)
            
            # Split training data for hyperparameter tuning
            train_data, validation_data = data.randomSplit([0.8, 0.2], seed=42)
            
            # Cache splits for faster access
            train_data.cache()
            validation_data.cache()
            
            logger.info(f"Train: {train_data.count()}, Validation: {validation_data.count()}, Test: {test_data.count()}")
            
            # Fast hyperparameter search
            logger.info("Starting hyperparameter optimization...")
            best_model, best_params, best_validation_rmse = fast_hyperparameter_search(
                train_data, validation_data
            )
            
            # Final evaluation on test set
            logger.info("Evaluating best model on test set...")
            test_metrics = evaluate_model_performance(best_model, test_data)
            
            # Log final metrics
            mlflow.log_params(best_params)
            mlflow.log_metric("validation_rmse", best_validation_rmse)
            mlflow.log_metrics(test_metrics)
            
            # Save model with MLflow
            logger.info("Saving model...")
            mlflow.spark.log_model(
                best_model,
                "recommendation_model",
                registered_model_name="wellness-recommendation-model"
            )
            
            # Performance summary
            logger.info("=" * 50)
            logger.info("TRAINING COMPLETE")
            logger.info(f"Best Parameters: {best_params}")
            logger.info(f"Validation RMSE: {best_validation_rmse:.4f}")
            logger.info(f"Test RMSE: {test_metrics['rmse']:.4f}")
            logger.info(f"Test MAE: {test_metrics['mae']:.4f}")
            logger.info(f"Inference Time: {test_metrics['inference_time']:.2f}s")
            logger.info("=" * 50)
            
    finally:
        # Clean up Spark session
        spark.stop()
        logger.info("Spark session closed")

if __name__ == "__main__":
    main()
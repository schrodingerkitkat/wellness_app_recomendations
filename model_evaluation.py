from pyspark.sql import SparkSession
from pyspark.ml.evaluation import MulticlassClassificationEvaluator, BinaryClassificationEvaluator
from pyspark.mllib.evaluation import MulticlassMetrics, BinaryClassificationMetrics
from pyspark.sql.functions import col

def create_spark_session():
    return SparkSession.builder \
        .appName("ModelEvaluation") \
        .getOrCreate()

def evaluate_multiclass_predictions(predictions):
    """Evaluate multiclass model predictions with multiple metrics."""
    evaluator_accuracy = MulticlassClassificationEvaluator(predictionCol="prediction", labelCol="label", metricName="accuracy")
    evaluator_f1 = MulticlassClassificationEvaluator(predictionCol="prediction", labelCol="label", metricName="f1")
    evaluator_precision = MulticlassClassificationEvaluator(predictionCol="prediction", labelCol="label", metricName="weightedPrecision")
    evaluator_recall = MulticlassClassificationEvaluator(predictionCol="prediction", labelCol="label", metricName="weightedRecall")

    accuracy = evaluator_accuracy.evaluate(predictions)
    f1_score = evaluator_f1.evaluate(predictions)
    precision = evaluator_precision.evaluate(predictions)
    recall = evaluator_recall.evaluate(predictions)

    print(f"Multiclass Evaluation Metrics:")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"F1 Score: {f1_score:.4f}")
    print(f"Weighted Precision: {precision:.4f}")
    print(f"Weighted Recall: {recall:.4f}")

def evaluate_binary_predictions(predictions):
    """Evaluate binary classification model predictions with multiple metrics."""
    evaluator_auc = BinaryClassificationEvaluator(rawPredictionCol="rawPrediction", labelCol="label", metricName="areaUnderROC")
    auc = evaluator_auc.evaluate(predictions)

    # Convert predictions to RDD for evaluation using MulticlassMetrics
    prediction_rdd = predictions.select(col("prediction").cast("double"), col("label").cast("double")).rdd
    metrics = MulticlassMetrics(prediction_rdd)

    print(f"Binary Classification Evaluation Metrics:")
    print(f"Area Under ROC: {auc:.4f}")
    print(f"Confusion Matrix: {metrics.confusionMatrix().toArray()}")
    print(f"Precision: {metrics.precision(1.0):.4f}")
    print(f"Recall: {metrics.recall(1.0):.4f}")
    print(f"F1 Score: {metrics.fMeasure(1.0):.4f}")

def main():
    spark = create_spark_session()

    # Assuming predictions are stored in a DataFrame
    predictions_path = "s3://gold-bucket/model_predictions.csv"
    predictions = spark.read.csv(predictions_path, header=True, inferSchema=True)

    # Evaluate predictions based on the problem type (multiclass or binary)
    if "rawPrediction" in predictions.columns:
        evaluate_binary_predictions(predictions)
    else:
        evaluate_multiclass_predictions(predictions)

if __name__ == "__main__":
    main()

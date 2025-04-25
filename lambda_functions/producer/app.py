import boto3
import csv
import os
import logging
from io import StringIO
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3_client = boto3.client('s3')
kinesis_client = boto3.client('kinesis')

def lambda_handler(event, context):
    """
    AWS Lambda function to process S3 events, read CSV files from S3, and send each row to an Amazon Kinesis stream.
    Args:
        event (dict): The event data passed to the Lambda function, typically containing S3 event notifications.
        context (LambdaContext): The runtime information of the Lambda function.
    Returns:
        dict: A dictionary indicating the status of the function execution. 
              Example: {"status": "done"} or {"status": "error", "message": "Stream name not configured"}
    Environment Variables:
        KINESIS_STREAM_NAME (str): The name of the Kinesis stream to which the data will be sent.
    Event Structure:
        The `event` parameter is expected to contain an S3 event notification structure with the following format:
        {
            "Records": [
                {
                    "s3": {
                        "bucket": {
                            "name": "bucket-name"
                        },
                        "object": {
                            "key": "object-key"
                        }
                    }
                },
                ...
            ]
        }
    Processing Steps:
        1. Validate the presence of the KINESIS_STREAM_NAME environment variable.
        2. Iterate through the S3 event records in the event payload.
        3. For each record:
            - Fetch the CSV file from the specified S3 bucket and key.
            - Parse the CSV file using `csv.DictReader`.
            - Send each row of the CSV file to the Kinesis stream with the `trip_id` as the partition key.
        4. Log the progress and handle any exceptions that occur during processing.
    Raises:
        Exception: Logs and handles any exceptions that occur during file processing or Kinesis operations.
    """
    logger.info("Lambda function invoked with event: %s", json.dumps(event))
    
    stream_name = os.environ.get('KINESIS_STREAM_NAME')
    if not stream_name:
        logger.error("Environment variable 'KinesisStreamName' is not set.")
        return {"status": "error", "message": "Stream name not configured"}
    
    logger.info(f"Stream name: {stream_name}")

    for record in event.get('Records', []):
        bucket_name = record['s3']['bucket']['name']
        object_key = record['s3']['object']['key']
        logger.info(f"New file detected: s3://{bucket_name}/{object_key}")
        
        try:
            # Get CSV file content from S3
            logger.info(f"Fetching file from S3: Bucket={bucket_name}, Key={object_key}")
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            content = response['Body'].read().decode('utf-8')
            logger.info(f"Successfully fetched file content from S3: {object_key}")

            # Use csv.DictReader to parse rows
            csv_reader = csv.DictReader(StringIO(content))
            row_count = 0
            for row in csv_reader:
                row_count += 1
                trip_id = row.get('trip_id', 'unknown')
                logger.debug(f"Processing row {row_count}: {row}")

                kinesis_response = kinesis_client.put_record(
                    StreamName=stream_name,
                    Data=json.dumps(row),
                    PartitionKey=trip_id
                )
                logger.info(f"Sent trip_id {trip_id} to Kinesis: {kinesis_response}")

            logger.info(f"Processed {row_count} rows from file {object_key}")

        except Exception as e:
            logger.error(f"Error processing file {object_key}: {e}", exc_info=True)

    logger.info("Lambda function execution completed.")
    return {"status": "done"}

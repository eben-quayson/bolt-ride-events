import json
import boto3
import os
import logging
import base64
from boto3.dynamodb.conditions import Key

# Logging config
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE_NAME'])

def lambda_handler(event, context):
    """
    AWS Lambda function to process Kinesis stream events, decode the data, 
    merge it with existing records in a DynamoDB table, and save the updated records.
    Args:
        event (dict): The event data passed to the Lambda function, containing 
                      a list of records from the Kinesis stream.
        context (object): The runtime information of the Lambda function.
    Returns:
        dict: A response indicating the status of the function execution.
    The function performs the following steps:
    1. Logs the number of records received in the event.
    2. Iterates through each record in the event:
       - Decodes the base64-encoded data from the Kinesis record.
       - Parses the decoded JSON string into a Python dictionary.
       - Extracts the `trip_id` from the payload.
       - Fetches the existing record from the DynamoDB table using the `trip_id`.
       - Merges the new payload with the existing record.
       - Saves the merged record back to the DynamoDB table.
    3. Logs any errors encountered during processing of individual records.
    """
    logger.info("Lambda triggered with %d record(s)", len(event['Records']))

    for record in event['Records']:
        try:
            # Decode the base64-encoded 'data' field
            decoded_data = base64.b64decode(record['kinesis']['data']).decode('utf-8')
            logger.info("Decoded payload: %s", decoded_data)

            # Parse the decoded JSON string
            payload = json.loads(decoded_data)
            logger.info("Parsed payload: %s", payload)

            trip_id = payload['trip_id']

            # Fetch existing record if any
            existing_item = table.get_item(Key={'id': trip_id}).get('Item', {})
            logger.info(f"Existing item for {trip_id}: {existing_item}")

            # Merge new payload into existing item
            merged_item = {**existing_item, **payload}
            merged_item['id'] = trip_id  # Make sure key is preserved

            # Write back the merged item
            table.put_item(Item=merged_item)
            logger.info(f"Successfully merged and saved item for {trip_id}")

        except Exception as e:
            logger.error(f"Failed to process record: {record}")
            logger.error(f"Error: {e}")

    return {"status": "ok"}

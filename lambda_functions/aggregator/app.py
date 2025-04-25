import boto3
import os
import pandas as pd
from datetime import datetime
import logging
from boto3.dynamodb.conditions import Attr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

from boto3.dynamodb.conditions import Attr
s3 = boto3.client('s3')

def get_dynamodb_table():
    return boto3.resource("dynamodb").Table(os.environ["DYNAMODB_TABLE_NAME"])

def get_s3_client():
    return boto3.client("s3")

def scan_all_items():
    table = get_dynamodb_table()
    items = []
    last_evaluated_key = None

    filter_expression = (
        Attr('fare_amount').exists() & 
        Attr('estimated_fare_amount').exists()
    )

    while True:
        scan_kwargs = {
            'FilterExpression': filter_expression,
        }
        if last_evaluated_key:
            scan_kwargs['ExclusiveStartKey'] = last_evaluated_key
        
        response = table.scan(**scan_kwargs)
        items.extend(response['Items'])

        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

    return items


def lambda_handler(event, context):
    logger.info("Lambda function started.")
    s3 = get_s3_client()
    
    try:
        # Scan all completed trips
        logger.info("Scanning DynamoDB table for completed trips.")
        items = scan_all_items()  # Use the function that handles pagination
        logger.info(f"Retrieved {len(items)} items from DynamoDB.")

        if not items:
            logger.warning("No items found matching the filter.")
            return
        
        df = pd.DataFrame(items)
        df['fare_amount'] = pd.to_numeric(df['fare_amount'], errors='coerce')
        df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'])

        logger.info("Calculating KPIs.")
        kpis = df.groupby('pickup_datetime').agg(
            total_fare=pd.NamedAgg(column='fare_amount', aggfunc='sum'),
            count_trips=pd.NamedAgg(column='fare_amount', aggfunc='count'),
            average_fare=pd.NamedAgg(column='fare_amount', aggfunc='mean'),
            max_fare=pd.NamedAgg(column='fare_amount', aggfunc='max'),
            min_fare=pd.NamedAgg(column='fare_amount', aggfunc='min')
        ).reset_index()

        # Upload each day's KPI as a JSON file
        for _, row in kpis.iterrows():
            date_str = row['pickup_datetime'].strftime('%Y-%m-%d')
            filename = f'kpis/date={date_str}/kpi.json'
            logger.info(f"Uploading KPI for {date_str} to S3: {filename}.")
            s3.put_object(
                Bucket=os.environ['ATHENA_BUCKET_NAME'],
                Key=filename,
                Body=row.to_json(),
                ContentType='application/json'
            )
        logger.info("All KPIs uploaded successfully.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise

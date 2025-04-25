import pytest
import boto3
from unittest import mock
import pandas as pd
from datetime import datetime
import os
import logging

# temporarily set dirctory to avoid issues with pytest and lambda_handler import
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

from lambda_functions.aggregator.app import lambda_handler

# Mock environment variables
mock_environment = {
    'DYNAMODB_TABLE_NAME': 'test-trips-table',
    'ATHENA_BUCKET_NAME': 'test-athena-bucket'
    
}
from lambda_functions.aggregator.app import lambda_handler

# Mock data that DynamoDB would return
mock_dynamodb_data = [
    {
        'pickup_datetime': '2025-04-22T08:30:00',
        'fare_amount': 20.0,
        'estimated_fare_amount': 22.0
    },
    {
        'pickup_datetime': '2025-04-22T09:00:00',
        'fare_amount': 25.0,
        'estimated_fare_amount': 27.0
    },
    {
        'pickup_datetime': '2025-04-22T10:15:00',
        'fare_amount': 15.0,
        'estimated_fare_amount': 17.0
    }
]

@pytest.fixture
def mock_dynamodb():
    with mock.patch.dict('os.environ', mock_environment):
        # Mock DynamoDB resource
        mock_table = mock.Mock()
        mock_table.scan.return_value = {'Items': mock_dynamodb_data}
        with mock.patch('boto3.resource') as mock_boto_resource:
            mock_boto_resource.return_value.Table.return_value = mock_table
            yield mock_table

def test_lambda_handler(mock_dynamodb):
    # Mock S3 client for uploading results
    mock_s3 = mock.Mock()
    with mock.patch('boto3.client') as mock_boto_client:
        mock_boto_client.return_value = mock_s3
        
        # Simulate the Lambda function call
        event = {}
        context = {}
        lambda_handler(event, context)

        # Check that the DynamoDB scan was called once
        mock_dynamodb.scan.assert_called_once()

        # Check that the S3 put_object method was called with the expected KPI file
        mock_s3.put_object.assert_called()

        # Check the KPI calculations (aggregate by pickup_datetime)
        expected_kpis = pd.DataFrame({
            'pickup_datetime': [datetime(2025, 4, 22, 8, 30), datetime(2025, 4, 22, 9, 0), datetime(2025, 4, 22, 10, 15)],
            'total_fare': [20.0, 25.0, 15.0],
            'count_trips': [1, 1, 1],
            'average_fare': [20.0, 25.0, 15.0],
            'max_fare': [20.0, 25.0, 15.0],
            'min_fare': [20.0, 25.0, 15.0]
        })
        
        # Simulate KPI calculation for the provided data
        result_kpis = pd.DataFrame(mock_dynamodb_data).groupby('pickup_datetime').agg(
            total_fare=pd.NamedAgg(column='fare_amount', aggfunc='sum'),
            count_trips=pd.NamedAgg(column='fare_amount', aggfunc='count'),
            average_fare=pd.NamedAgg(column='fare_amount', aggfunc='mean'),
            max_fare=pd.NamedAgg(column='fare_amount', aggfunc='max'),
            min_fare=pd.NamedAgg(column='fare_amount', aggfunc='min')
        ).reset_index()
        
        result_kpis['pickup_datetime'] = pd.to_datetime(result_kpis['pickup_datetime'])

        # Assert if calculated KPIs match the expected output
        pd.testing.assert_frame_equal(result_kpis, expected_kpis)


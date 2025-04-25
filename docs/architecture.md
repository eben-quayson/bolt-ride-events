### **Architecture.md**

# Architecture Overview for the Lambda Function

This document outlines the architecture of the AWS Lambda function that processes completed trip data from DynamoDB, calculates Key Performance Indicators (KPIs), and uploads the results to an S3 bucket. It provides a high-level overview of the system components, their interactions, and how they contribute to the overall solution.

## 1. **System Components**

The system architecture consists of several AWS services working together to enable real-time trip data processing and KPI aggregation. The main components are:

1. **AWS Lambda** – A serverless compute service that runs the function to scan the DynamoDB table, calculate KPIs, and upload them to S3.
2. **Amazon DynamoDB** – A NoSQL database that stores the completed trip data, which includes trip attributes like `fare_amount` and `estimated_fare_amount`.
3. **Amazon S3** – A cloud storage service that holds the KPI files for each day, organized by date.
4. **Amazon CloudWatch Logs** – Used for logging Lambda function execution details, including errors and process steps.
5. **AWS Identity and Access Management (IAM)** – Used to control the permissions for each AWS service involved in the system.
6. **AWS KMS** – Optional, for encrypting sensitive data in DynamoDB and S3.

## 2. **High-Level Architecture Diagram**

Below is the architecture diagram that illustrates the flow of data between the components:

```plaintext
+-------------------+     +-----------------+     +-----------------+  
|  DynamoDB Table   |---->|   AWS Lambda    |---->|   Amazon S3     |  
|  (Completed Trip  |     |   (KPI Processing)|     |   (KPI Storage)  |  
|  Data)            |     |   & Aggregation |     |   (Daily KPIs)   |  
+-------------------+     +-----------------+     +-----------------+  
               |                     |                      |
               |                     v                      v
               |              +----------------+     +-----------------+
               |              |  CloudWatch    |     | AWS IAM Role    |
               |              |  Logs          |     | (Access Control)|
               |              +----------------+     +-----------------+
               |                                           
```

## 3. **Detailed Workflow**

### 3.1 **DynamoDB: Data Storage**

- The **Amazon DynamoDB** table stores all the trip data. Each trip includes attributes such as `fare_amount`, `estimated_fare_amount`, and `pickup_datetime`.
- The data is constantly updated as trip events are processed, and the Lambda function periodically scans the table to extract relevant completed trip data for KPI calculation.
  
  Key considerations:
  - **Table Name**: The DynamoDB table is accessed using the `DYNAMODB_TABLE_NAME` environment variable.
  - **Scan Query**: The Lambda function scans the table to retrieve trips with the necessary attributes (`fare_amount` and `estimated_fare_amount`).

### 3.2 **AWS Lambda: KPI Processing and Aggregation**

- **Lambda Execution**: AWS Lambda is the core component for processing the trip data. It is triggered by the DynamoDB scan operation and performs the following tasks:
  - **Scan DynamoDB**: The Lambda function scans the entire table to find records where both `fare_amount` and `estimated_fare_amount` exist.
  - **Data Processing with Pandas**: The Lambda function converts the DynamoDB data into a Pandas DataFrame to facilitate KPI calculations.
  - **KPI Calculation**: It aggregates the data by `pickup_datetime` to calculate the following KPIs:
    - Total Fare
    - Trip Count
    - Average Fare
    - Max Fare
    - Min Fare
  - **Data Upload to S3**: The calculated KPIs are then uploaded as JSON files to an Amazon S3 bucket.

  Key considerations:
  - **Concurrency**: The Lambda function is designed to handle multiple invocations concurrently, but to avoid throttling or rate limits, the maximum concurrent executions should be monitored and adjusted as needed.
  - **Execution Time**: DynamoDB scans can be large; however, Lambda has a maximum execution time of 15 minutes. If necessary, the scan operation could be broken into smaller chunks (using pagination) to avoid timing out.
  - **Environment Variables**: The Lambda function relies on environment variables (`DYNAMODB_TABLE_NAME` and `ATHENA_BUCKET_NAME`) to determine which DynamoDB table and S3 bucket to interact with.

### 3.3 **Amazon S3: KPI Storage**

- **Storage of KPI Files**: Once the KPIs are calculated, the results are uploaded to an S3 bucket. Each file is stored under a folder structure based on the date of the trip (`/kpis/date=<date>/kpi.json`).
- **Bucket Organization**: The S3 bucket is used to organize the KPIs by date. This allows for easy querying and visualization of daily performance.
  
  Key considerations:
  - **Server-Side Encryption (SSE)**: It's crucial to enable encryption at rest for data stored in S3. You can use either SSE-S3 (default encryption) or SSE-KMS for more control over the encryption keys.
  - **Access Control**: The Lambda function should have specific IAM permissions (e.g., `s3:PutObject`) to upload the KPI files to the S3 bucket.

### 3.4 **CloudWatch Logs: Logging and Monitoring**

- **Logging Lambda Execution**: CloudWatch Logs is used to log the execution flow of the Lambda function. This includes:
  - Lambda function startup
  - Number of items retrieved from DynamoDB
  - KPI calculations
  - Upload success or failure to S3
  
- **CloudWatch Alarms**: Set up CloudWatch alarms to notify the team of any failures or anomalies, such as Lambda errors or slow function performance.

  Key considerations:
  - **Log Retention**: CloudWatch logs can be configured with a retention policy. Depending on the use case, the logs can be retained for a specific period (e.g., 30 days).

### 3.5 **IAM Roles and Policies**

- **Lambda Execution Role**: The Lambda function needs an IAM execution role with the following policies:
  - **DynamoDB**: Permissions to `scan` or `query` the DynamoDB table.
  - **S3**: Permissions to `PutObject` to the target S3 bucket.
  - **CloudWatch Logs**: Permissions to write logs to CloudWatch.

  Example policies (as shown in the **Security.md** document):
  - **Lambda Basic Execution Role**: Provides permissions for logging to CloudWatch.
  - **Custom DynamoDB Policy**: Provides read access to the DynamoDB table.
  - **Custom S3 Policy**: Provides write access to the S3 bucket.

- **Role Permissions**: Make sure that all roles are granted the **least privilege** and are restricted to only the necessary actions.

### 3.6 **Optional: AWS KMS for Encryption**

- **DynamoDB Encryption**: DynamoDB encrypts all data at rest by default. However, using **AWS Key Management Service (KMS)** allows for more granular control over encryption keys.
- **S3 Encryption**: Enable server-side encryption using **SSE-KMS** or **SSE-S3** for storing KPI data in S3. For added security, consider using customer-managed keys (CMK) with KMS.

## 4. **Resilience and Fault Tolerance**

- **Retry Logic**: The Lambda function automatically retries on certain errors, such as network timeouts. However, long-running tasks like DynamoDB scans may need to handle pagination and retry logic.
- **Lambda Timeout and Memory**: Lambda function timeouts and memory settings should be appropriately configured. For long-running tasks, ensure that the function’s timeout is set to the maximum allowed (15 minutes).
- **Error Handling**: Use structured error handling to capture and log errors in CloudWatch Logs. This allows the team to troubleshoot and respond to issues promptly.

## 5. **Security and Access Control**

For detailed security measures and access control, refer to the **Security.md** document, which outlines the policies, encryption, and access management best practices for Lambda, DynamoDB, and S3.

---

This **Architecture.md** document outlines the end-to-end architecture for processing completed trip data using AWS Lambda, DynamoDB, and S3, and emphasizes the integration of these AWS services. It also covers critical architectural considerations such as data security, logging, and error handling to ensure robustness and reliability of the system.
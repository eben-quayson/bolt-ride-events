### **Security.md**

# Security Considerations for the Lambda Function

This document provides an in-depth overview of the security considerations for the AWS Lambda function that processes completed trip data from DynamoDB, calculates KPIs, and uploads the results to an S3 bucket.

## 1. **IAM Role and Permissions**

### 1.1 **Lambda Execution Role**
The Lambda function requires specific AWS Identity and Access Management (IAM) permissions to interact with AWS resources such as DynamoDB, S3, and CloudWatch Logs. The Lambda execution role should be configured with the **least privilege principle**, ensuring that the function only has the necessary permissions.

### 1.2 **Policies to Attach**
- **`AWSLambdaBasicExecutionRole`**: Provides the necessary permissions for the Lambda function to write logs to CloudWatch.
- **Custom Policy for DynamoDB**: The Lambda function must have permission to read from the DynamoDB table. Attach a policy that allows the `scan` or `query` actions for the DynamoDB table.
- **Custom Policy for S3**: The Lambda function needs permission to write objects to S3. Attach a policy that grants the `s3:PutObject` action for the target bucket.
- **CloudWatch Logs Permissions**: The Lambda function needs permission to create log groups and streams and write log events to CloudWatch.

### Example IAM Policy for Lambda Execution Role:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:Scan",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:<region>:<account-id>:table/<table-name>"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::<bucket-name>/*"
        }
    ]
}
```

### 1.3 **Key Security Best Practices**
- **Use Role-based Access Control (RBAC)**: Ensure that only the Lambda execution role has the necessary permissions to access DynamoDB and S3.
- **Avoid Using Root Account**: Never grant permissions directly to the root account or unnecessary accounts. Always use an IAM role for Lambda and specific policies to grant access.
- **Regularly Rotate Keys**: If your Lambda function is using AWS access keys (which it ideally shouldn't), ensure that they are rotated regularly. Use IAM roles wherever possible to avoid key management overhead.

## 2. **Data Protection**

### 2.1 **Encryption in Transit**
- **HTTPS**: All data transferred between AWS services (e.g., DynamoDB, S3, CloudWatch Logs) should be encrypted in transit using HTTPS to prevent data interception.
- **VPC Security**: If the Lambda function needs to access resources in a VPC (Virtual Private Cloud), ensure that the necessary security groups and network ACLs are in place to control inbound and outbound traffic.

### 2.2 **Encryption at Rest**

- **DynamoDB Encryption**: DynamoDB supports **encryption at rest** by default. Ensure that the DynamoDB table is using this feature. This encrypts the data stored in the table and ensures that sensitive information is protected.
  
- **S3 Server-Side Encryption**: Enable server-side encryption (SSE) for the S3 bucket where KPIs are stored. This ensures that all objects stored in the bucket are encrypted at rest.
  - Use **SSE-S3** (Amazon S3 managed keys) or **SSE-KMS** (AWS Key Management Service) for encryption.
  - For added control, **SSE-KMS** can be used to manage encryption keys, providing fine-grained access control to who can use and manage encryption keys.

### Example Code to Enable S3 Server-Side Encryption:
```python
s3.put_object(
    Bucket=os.environ['ATHENA_BUCKET_NAME'],
    Key=filename,
    Body=row.to_json(),
    ContentType='application/json',
    ServerSideEncryption='AES256'  # or 'aws:kms' for SSE-KMS
)
```

### 2.3 **Environment Variables Security**
Sensitive information, such as DynamoDB table names, S3 bucket names, and other configuration settings, should be stored securely in Lambda environment variables.
- **Environment Variables**: Ensure that only the Lambda function has access to the environment variables and that they are not exposed in logs or error messages.
- **Use Encryption for Environment Variables**: For sensitive data, consider enabling encryption of Lambda environment variables using AWS KMS.

### 2.4 **Access to Lambda Environment Variables**
Ensure that only the Lambda execution role has the necessary permissions to access and modify the environment variables, and restrict access to other entities.

## 3. **Audit and Monitoring**

### 3.1 **CloudWatch Logs**
- **Enable Detailed Logging**: Ensure that detailed logging is enabled for the Lambda function, including logs of successful KPI uploads and any errors or exceptions.
- **Log Sensitivity**: Avoid logging sensitive data such as full trip details, fares, or other personally identifiable information (PII). Instead, log general activity like function start, end, and success or failure status.
  
  **Example Log Entry**:
  ```python
  logger.info(f"Uploading KPI for {date_str} to S3: {filename}.")
  ```

### 3.2 **CloudTrail and CloudWatch Alarms**
- **AWS CloudTrail**: Enable CloudTrail logging to capture all API calls to AWS services. This includes access to DynamoDB, S3, and Lambda invocations, providing an audit trail.
- **CloudWatch Alarms**: Set up CloudWatch Alarms to notify you if any abnormal activity occurs, such as unexpected Lambda function failures, slow performance, or large numbers of errors.

### 3.3 **DynamoDB Streams**
If real-time updates are necessary, use **DynamoDB Streams** to capture changes (e.g., inserted, updated, or deleted items) from the table. DynamoDB Streams provide a time-ordered sequence of changes, which can be processed to update KPIs in real-time or trigger additional actions.

## 4. **Security Vulnerabilities and Updates**

### 4.1 **Third-Party Libraries and Dependencies**
- **Dependency Scanning**: Regularly scan the dependencies in your Lambda function (if you are using any external libraries) for known security vulnerabilities. Use tools such as **AWS CodeGuru** or **OWASP Dependency-Check** to identify and address vulnerabilities in your libraries.
  
### 4.2 **Security Patches and Updates**
- **Lambda Runtime**: Ensure that your Lambda function is using a supported runtime version (e.g., Python 3.x). AWS provides security patches for Lambda runtimes, so keeping the runtime up-to-date ensures that your Lambda function benefits from the latest security fixes.
  
### 4.3 **Code Review and Audits**
- **Code Review**: Regularly conduct code reviews to identify potential security issues. Focus on areas where sensitive data is processed or transmitted.
- **Vulnerability Scanning**: Use security scanning tools (such as AWS Inspector or third-party solutions) to identify potential vulnerabilities in your Lambda function code.

## 5. **Access Control and Least Privilege**

### 5.1 **Principle of Least Privilege**
The Lambda execution role should only have the minimum permissions necessary to perform its tasks. Avoid using overly broad permissions like `*` (wildcard) permissions unless absolutely necessary. This minimizes the attack surface and reduces the impact of any potential security breach.

### 5.2 **Security Groups and VPC**
If your Lambda function interacts with resources in a VPC, make sure that:
- **Security Groups**: Proper security groups are configured to limit inbound and outbound traffic to only the necessary resources.
- **VPC Peering**: If the Lambda function communicates with other AWS resources over VPC peering, ensure that only the necessary VPCs can access each other.

## 6. **Incident Response and Recovery**

### 6.1 **Error Handling and Alerts**
Set up **CloudWatch Alarms** for Lambda execution failures, which will immediately notify the team if there’s an issue with the function's performance or logic.

### 6.2 **Backup and Disaster Recovery**
- **S3 Backup**: Since KPIs are stored in S3, ensure that backups are available for the stored data, or consider using **S3 versioning** for maintaining historical versions of the KPI data.
- **DynamoDB Backup**: Enable **DynamoDB On-Demand Backup** or use **DynamoDB Streams** for disaster recovery.

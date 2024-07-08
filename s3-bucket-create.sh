#!/bin/bash

MAX_RETRIES=20
WAIT_SECONDS=5

for ((i=1; i<=MAX_RETRIES; i++)); do
    echo "Attempt $i: Creating S3 bucket..."
    awslocal s3api create-bucket --bucket sds-local --region us-east-1 && break
    echo "LocalStack S3 not yet available, retrying in $WAIT_SECONDS seconds..."
    sleep $WAIT_SECONDS
done

# Create S3 bucket
echo "Creating S3 bucket..."
awslocal --endpoint-url=http://localhost:4566 s3api create-bucket --bucket sds-local --region us-east-1

# Verify bucket creation
echo "Listing S3 buckets..."
awslocal --endpoint-url=http://localhost:4566 s3 ls

echo "S3 bucket creation script completed."

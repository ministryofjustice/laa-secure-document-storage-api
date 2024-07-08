#!/bin/bash

# Wait for LocalStack S3 service to be healthy
echo "Waiting for LocalStack S3 to be healthy..."
until awslocal --endpoint-url=http://localhost:4566 s3 ls >/dev/null 2>&1; do
    echo "LocalStack S3 not yet available, retrying in 5 seconds..."
    sleep 5
done

# Create S3 bucket
echo "Creating S3 bucket..."
awslocal --endpoint-url=http://localhost:4566 s3api create-bucket --bucket sds-local --region us-east-1

# Verify bucket creation
echo "Listing S3 buckets..."
awslocal --endpoint-url=http://localhost:4566 s3 ls

echo "S3 bucket creation script completed."

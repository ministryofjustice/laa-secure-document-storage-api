#!/bin/bash

MAX_RETRIES=20
WAIT_SECONDS=5
FILE_TO_UPLOAD="README.md"  # Set your filename here


# Wait for the localstack to be ready before creating the S3 bucket
echo "Waiting for localstack to be ready..."
for i in $(seq 1 $MAX_RETRIES); do
  nc -z localhost 4566 && break
  echo "Localstack is not ready yet. Retrying in $WAIT_SECONDS seconds..."
  sleep $WAIT_SECONDS
done

aws --endpoint-url=http://localhost:4566 s3api create-bucket --bucket sds-local --region us-east-1


# Verify bucket creation
echo "Listing S3 buckets..."
aws --endpoint-url=http://localhost:4566 s3 ls

# Upload the file to the bucket
echo "Uploading file to S3 bucket..."
aws --endpoint-url=http://localhost:4566 s3 cp $FILE_TO_UPLOAD s3://sds-local/$FILE_TO_UPLOAD
aws --endpoint-url=http://localhost:4566 s3 cp $FILE_TO_UPLOAD s3://sds-local/CRM14/$FILE_TO_UPLOAD


echo "S3 bucket creation and file uploading script completed."
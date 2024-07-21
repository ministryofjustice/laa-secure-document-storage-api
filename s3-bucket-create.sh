#!/bin/bash

MAX_RETRIES=20
WAIT_SECONDS=5
FILE_TO_UPLOAD="README.md"  # Set your filename here


awslocal s3api create-bucket --bucket sds-local --region us-east-1 && break


# Verify bucket creation
echo "Listing S3 buckets..."
awslocal --endpoint-url=http://localhost:4566 s3 ls

# Upload the file to the bucket
echo "Uploading file to S3 bucket..."
awslocal --endpoint-url=http://localhost:4566 s3 cp $FILE_TO_UPLOAD s3://sds-local/$FILE_TO_UPLOAD
awslocal --endpoint-url=http://localhost:4566 s3 cp $FILE_TO_UPLOAD s3://sds-local/CRM14/$FILE_TO_UPLOAD


echo "S3 bucket creation and file uploading script completed."
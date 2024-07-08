#!/bin/bash

# Create the S3 bucket using awscli and LocalStack endpoint
aws --endpoint-url=http://localhost:4566 s3 mb s3://sds-local

awslocal s3api \
create-bucket --bucket sds-local \
--region us-east-1
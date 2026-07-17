#!/usr/bin/env bash
AUDIT_TABLE_NAME="AUDIT_SDS"
FILE_TO_UPLOAD="README.md"

# Prepare bucket and folder structure with an initial upload
echo "SAMPLE CONTENT $(date +%F)" > $FILE_TO_UPLOAD
awslocal s3api create-bucket --bucket sds-local --create-bucket-configuration LocationConstraint=eu-west-1
awslocal s3api put-bucket-versioning --bucket sds-local --versioning-configuration Status=Enabled
awslocal s3 cp $FILE_TO_UPLOAD s3://sds-local/$FILE_TO_UPLOAD
awslocal s3 cp $FILE_TO_UPLOAD s3://sds-local/CRM14/$FILE_TO_UPLOAD

# Make config files bucket and copy the config files into it
# Note:
# - environmet vars from sds-api section of docker-compose.yml are NOT available here
# - We're copying from the Localstack container, not locally, so need mapped volume with config files.
awslocal s3api create-bucket --bucket sds-client-configs --create-bucket-configuration LocationConstraint=eu-west-1
awslocal s3api put-bucket-versioning --bucket sds-client-configs --versioning-configuration Status=Enabled
awslocal s3 cp /clientconfigs s3://sds-client-configs/ --recursive

# Initialise audit table - with per-event format
awslocal --region eu-west-1 dynamodb create-table --table-name $AUDIT_TABLE_NAME \
    --attribute-definitions AttributeName=request_id,AttributeType=S AttributeName=filename_position,AttributeType=N \
    --key-schema AttributeName=request_id,KeyType=HASH AttributeName=filename_position,KeyType=RANGE \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

awslocal --region eu-west-1 dynamodb wait table-exists --table-name $AUDIT_TABLE_NAME

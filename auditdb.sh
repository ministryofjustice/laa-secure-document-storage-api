#!/bin/sh

TABLE_NAME="AUDIT_SDS"
ENDPOINT_URL="http://localhost:8100"
REGION="eu-west-1"

# Export AWS credentials if not already set in environment
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
export AWS_DEFAULT_REGION=$REGION

# Check if the table exists
if ! aws dynamodb list-tables --region $REGION --endpoint-url $ENDPOINT_URL | grep -q "$TABLE_NAME"; then
   # Create the table
   aws dynamodb create-table --region $REGION --table-name $TABLE_NAME \
    --attribute-definitions AttributeName=service_id,AttributeType=S AttributeName=file_id,AttributeType=S \
    --key-schema AttributeName=service_id,KeyType=HASH AttributeName=file_id,KeyType=RANGE \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --endpoint-url $ENDPOINT_URL

    # Wait for the table to be created
    aws dynamodb wait table-exists --region $REGION --table-name $TABLE_NAME --endpoint-url $ENDPOINT_URL
fi

# Put an item into the table
aws dynamodb put-item --region $REGION --table-name $TABLE_NAME --item \
'{
  "service_id": {"S": "1235"},
  "file_id": {"S": "file2"},
  "operation": {"S": "Read"}
}' --endpoint-url $ENDPOINT_URL

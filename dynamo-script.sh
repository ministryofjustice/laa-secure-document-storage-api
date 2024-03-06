#!/bin/sh

TABLE_NAME="SERVICE_CONFIG"

if ! aws dynamodb list-tables --endpoint-url http://localhost:8100 | grep -q "$TABLE_NAME"; then
    aws dynamodb create-table --table-name $TABLE_NAME \
    --attribute-definitions AttributeName=service_id,AttributeType=S \
    --key-schema AttributeName=service_id,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --endpoint-url http://localhost:8100


    aws dynamodb wait table-exists --table-name $TABLE_NAME \
    --endpoint-url http://localhost:8100
fi

aws dynamodb put-item --table-name SERVICE_CONFIG --item \
'{
  "service_id": {"S": "1234"},
  "acceptedExtensions": {"SS": [".pdf", ".doc", ".docx", ".txt"]},
  "acceptedContentTypes": {"SS": ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]}
}' --endpoint-url http://localhost:8100
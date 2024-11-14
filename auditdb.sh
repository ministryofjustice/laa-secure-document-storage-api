#!/bin/sh
UNABLE_TO_CONNECT=255
TABLE_NAME="AUDIT_SDS"

until aws --region eu-west-1 dynamodb list-tables --endpoint-url http://localhost:8100; do
  if [ $? -eq $UNABLE_TO_CONNECT ]; then
    echo "Unable to connect, trying again in 1 second"
    sleep 1
  else
    echo "Unexpected issue: RC $?"
    exit $UNABLE_TO_CONNECT
  fi
done

if ! aws --region eu-west-1 dynamodb list-tables --endpoint-url http://localhost:8100 | grep -q "$TABLE_NAME"; then
   aws --region eu-west-1 dynamodb create-table --table-name $TABLE_NAME \
    --attribute-definitions AttributeName=service_id,AttributeType=S AttributeName=file_id,AttributeType=S \
    --key-schema AttributeName=service_id,KeyType=HASH AttributeName=file_id,KeyType=RANGE \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --endpoint-url http://localhost:8100

    aws --region eu-west-1 dynamodb wait table-exists --table-name $TABLE_NAME \
    --endpoint-url http://localhost:8100
fi

aws --region eu-west-1 dynamodb put-item --table-name $TABLE_NAME --item \
'{
  "service_id": {"S": "1235"},
  "file_id": {"S": "file2"},
  "operation": {"S": "Read"}
}' --endpoint-url http://localhost:8100

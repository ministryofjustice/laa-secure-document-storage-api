#!/usr/bin/env bash
UNABLE_TO_CONNECT=255
TABLE_NAME="CONFIG_SDS"
REGION=${AWS_REGION:'-eu-west-2'}

until aws --region "$REGION" dynamodb list-tables --endpoint-url http://localhost:8100; do
  if [ $? -eq $UNABLE_TO_CONNECT ]; then
    echo "Unable to connect, trying again in 1 second"
    sleep 1
  else
    echo "Unexpected issue: RC $?"
    exit $UNABLE_TO_CONNECT
  fi
done

if ! aws --region "$REGION" dynamodb list-tables --endpoint-url http://localhost:8100 | grep -q "$TABLE_NAME"; then
  aws --region "$REGION" dynamodb create-table \
      --table-name $TABLE_NAME \
      --key-schema \
          AttributeName=client,KeyType=HASH  \
      --attribute-definitions \
          AttributeName=client,AttributeType=S \
      --provisioned-throughput \
          ReadCapacityUnits=5,WriteCapacityUnits=5 \
      --endpoint-url http://localhost:8100

    aws --region "$REGION" dynamodb wait table-exists --table-name $TABLE_NAME \
    --endpoint-url http://localhost:8100
fi

aws --region "$REGION" dynamodb describe-table --table-name $TABLE_NAME --endpoint-url http://localhost:8100

aws --region "$REGION" dynamodb put-item --table-name $TABLE_NAME --item \
'{
  "client": {"S": "sds-local"},
  "service_id": {"S": "sds-local"},
  "bucket_name": {"S": "sds-deadletter"},
  "region_name": {"S": "'"$REGION"'"}
}' \
--endpoint-url http://localhost:8100
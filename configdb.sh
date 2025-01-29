#!/usr/bin/env bash
UNABLE_TO_CONNECT=255
TABLE_NAME=${CONFIG_TABLE:-"CONFIG_SDS"}
REGION="eu-west-2"

if [[ "$DEPLOYMENT_ENV" == "local" ]]; then
  ENDPOINT_SPEC="--region=$REGION --endpoint-url http://localhost:8100"
else
  echo "** PRODUCTION **"
  ENDPOINT_SPEC="--region=$REGION"
fi

if [ "$1" != "init" ] && [ "$1" != "client" ]; then
  echo "Invalid argument. Please use 'init' or 'client'"
  exit 1
fi

# Wait for the connection to be ready
until aws --region "$REGION" dynamodb list-tables --endpoint-url http://localhost:8100; do
  if [ $? -eq $UNABLE_TO_CONNECT ]; then
    echo "Unable to connect, trying again in 1 second"
    sleep 1
  else
    echo "Unexpected issue: RC $?"
    exit $UNABLE_TO_CONNECT
  fi
done

# Check if table needs to be initialised
TABLE_EXISTS=$(aws $ENDPOINT_SPEC dynamodb list-tables | grep "$TABLE_NAME")
if [ -z "$TABLE_EXISTS" ]; then
  # Initialise then exit
  echo "Initialising the table"
  if ! aws $ENDPOINT_SPEC dynamodb list-tables | grep -q "$TABLE_NAME"; then
    aws $ENDPOINT_SPEC dynamodb create-table \
        --table-name $TABLE_NAME \
        --key-schema \
            AttributeName=client,KeyType=HASH  \
        --attribute-definitions \
            AttributeName=client,AttributeType=S \
        --provisioned-throughput \
            ReadCapacityUnits=5,WriteCapacityUnits=5

    aws $ENDPOINT_SPEC dynamodb wait table-exists --table-name $TABLE_NAME
  fi
  aws $ENDPOINT_SPEC dynamodb describe-table --table-name $TABLE_NAME
fi

# If all we needed to do was make sure the table exists, that should be done by this point.
if [ "$1" == "init" ]; then
  echo "Table $TABLE_NAME initialised"
  exit 0
fi

# Create a client config from this point forwards

CLIENT=${2:-"$CLIENT"}
BUCKET_NAME=${3:-"$BUCKET_NAME"}
SERVICE_ID=${4:-"$CLIENT"}

# If CLIENT is empty, prompt for the value
if [ -z "$CLIENT" ]; then
  read -p "Enter client id: " CLIENT
fi

# If BUCKET_NAME is empty, prompt for the value
if [ -z "$BUCKET_NAME" ]; then
  read -p "Enter bucket name: " BUCKET_NAME
fi

# If SERVICE_ID is empty, prompt for the value
if [ -z "$SERVICE_ID" ]; then
  read -p "Enter service id (default: $SERVICE_ID): " SERVICE_ID
fi

echo ""
echo "Client : $CLIENT"
echo "Service: $SERVICE_ID"
echo "Bucket : $BUCKET_NAME"
echo ""
echo "Adding client config to $TABLE_NAME $ENDPOINT_SPEC"

# Prompt to continue
read -p "Continue? (y/n) " -n 1 -r RESPONSE
echo ""
if [[ ! $RESPONSE =~ ^[Yy]$ ]]; then
  echo "Exiting"
  exit 0
fi

# Check if a record with key CLIENT_ID already exists
if aws $ENDPOINT_SPEC dynamodb get-item --table-name "$TABLE_NAME" --key '{"client": {"S": "'"$CLIENT"'"}}' | grep -q "Item"; then
  echo "Client $CLIENT already exists"
  exit 1
fi

aws $ENDPOINT_SPEC dynamodb put-item --table-name "$TABLE_NAME" --item \
'{
  "client": {"S": "'"$CLIENT"'"},
  "service_id": {"S": "'"$SERVICE_ID"'"},
  "bucket_name": {"S": "'"$BUCKET_NAME"'"},
  "file_validators": {"L": []}
}' || echo "Error whilst adding client config" && exit 1

echo "Client config added"

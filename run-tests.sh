#!/bin/bash

# Path to the Postman collection
COLLECTION_PATH="/Users/mohammed.latif/Postman/files/laa-secure-document-storage/SecureDocStoreAPI.postman_collection.json"

# Path to the Postman environment
ENVIRONMENT_PATH="/Users/mohammed.latif/Postman/files/laa-secure-document-storage/Environment.json"

# Check if the collection file exists
if [ ! -f "$COLLECTION_PATH" ]; then
  echo "Error: Collection file not found at $COLLECTION_PATH"
  exit 1
fi

# Check if the environment file exists
if [ ! -f "$ENVIRONMENT_PATH" ]; then
  echo "Error: Environment file not found at $ENVIRONMENT_PATH"
  exit 1
fi

# Run the Newman command
newman run "$COLLECTION_PATH" --environment "$ENVIRONMENT_PATH"

# Check if the Newman command succeeded
if [ $? -eq 0 ]; then
  echo "Newman tests ran successfully."
else
  echo "Error: Newman tests failed."
  exit 1
fi

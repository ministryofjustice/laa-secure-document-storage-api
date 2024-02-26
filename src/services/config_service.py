import os
import boto3
from models.config.file_types_config import AcceptedFileTypes


class DynamoDBService:
    _instance = None

    @staticmethod
    def get_instance():
        if DynamoDBService._instance is None:
            DynamoDBService()
        return DynamoDBService._instance

    def __init__(self):
        if DynamoDBService._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            DynamoDBService._instance = self

        table_name = os.getenv('CONFIG_TABLE', 'SERVICE_CONFIG')

        # Check whether the application is running in a local development
        # environment or in production
        is_local = os.getenv('IS_LOCAL', False)

        if is_local:
            self._dynamodb = boto3.resource('dynamodb', endpoint_url='http://localhost:8000')
        else:
            region_name = os.getenv('AWS_REGION', 'us-east-1')
            self._dynamodb = boto3.resource('dynamodb', region_name=region_name)

        self._config = self._dynamodb.Table(table_name)

    def read_config(self, key: str) -> AcceptedFileTypes:
        response = self._config.get_item(Key={'service_id': key})
        item = response.get('Item')

        if not item:
            return None

        config = AcceptedFileTypes(**item)
        return config


async def get_accepted_file_type_config(key:str) -> AcceptedFileTypes:
    dynamodb_service = DynamoDBService.get_instance()
    return dynamodb_service.read_config(key)


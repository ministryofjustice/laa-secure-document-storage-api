import boto3
import os
from dotenv import load_dotenv
import structlog
from datetime import datetime

from src.utils.operation_types import OperationType

logger = structlog.get_logger()

load_dotenv()


class AuditService:

    _instance = None

    @staticmethod
    def getInstance():
        """ Static access method. """
        if AuditService._instance is None:
            AuditService()
        return AuditService._instance

    def __init__(self):
        """ Virtually private constructor. """
        if AuditService._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            AuditService._instance = self
            self.dynamodb_client = self.get_dynamodb_client()

    def get_dynamodb_client(self):
        if os.getenv('ENV') != 'local':
            logger.info("Using production DynamoDB client")
            dynamodb_client = boto3.resource('dynamodb',   region_name=os.getenv('AWS_REGION'))
        else:
            logger.info("Using local DynamoDB client")
            dynamodb_client = boto3.resource(
                'dynamodb',
                region_name=os.getenv('AWS_REGION'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                endpoint_url=os.getenv('DYNAMODB_ENDPOINT_URL')
            )

        return dynamodb_client


def put_item(service_id: str, file_id: str, operation: OperationType):
    auditDb = AuditService.getInstance()
    dynamodb_resource = auditDb.dynamodb_client  # this retrieves the DynamoDB resource
    table = dynamodb_resource.Table(os.getenv('AUDIT_TABLE'))  # use the resource to get the Table

    identifier = {
        'service_id': service_id,
        'file_id': file_id
    }

    response = table.get_item(Key=identifier)

    if 'Item' not in response:
        logger.debug(f'Item with service_id={service_id}, file_id={file_id} not found. Creating new item.')

        operation_history = [
            {
                'OPERATION_TYPE': operation.name,
                'OPERATION_TIME': datetime.now().isoformat()  # replace with your way of getting time
            }
        ]

        item = {
            **identifier,
            'operation_history': operation_history,
            'created_on': datetime.now().isoformat(),
            'last_updated_on': datetime.now().isoformat(),
        }

        table.put_item(Item=item)

    # If the item does exist, update the item and append the operation to operation_history
    else:
        print(f'Item with service_id={service_id}, file_id={file_id} found. Updating operation_history.')
        item = response.get("Item")
        operation_history = item['operation_history']
        operation_history.append({'OPERATION_TYPE': operation.name, 'OPERATION_TIME': datetime.now().isoformat()})
        item['operation_history'] = operation_history
        item["last_updated_on"] = datetime.now().isoformat()

        table.put_item(Item=item)


def get_all_items():
    tbl = os.getenv('AUDIT_TABLE')
    logger.info("Table name is {}".format(tbl))
    auditDb = AuditService.getInstance()
    table = auditDb.dynamodb_client.Table(tbl)
    response = table.scan()
    return response['Items']

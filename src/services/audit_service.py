import boto3
import os

from botocore.exceptions import ClientError
from dotenv import load_dotenv
import structlog
from src.models.status_report import ServiceObservations, Category
from src.models.audit_record import AuditRecord
from src.utils.status_reporter import StatusReporter

logger = structlog.get_logger()

load_dotenv()


class AuditService:

    _instance = None

    @staticmethod
    def get_instance():
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


def put_item(audit_record: AuditRecord):
    auditDb = AuditService.get_instance()
    dynamodb_resource = auditDb.dynamodb_client
    table_name = os.getenv('AUDIT_TABLE')
    if not table_name:
        raise ValueError("Failed to get value from AUDIT_TABLE environment variable")
    table = dynamodb_resource.Table(table_name)
    table.put_item(Item=audit_record.model_dump())


class AuditServiceStatusReporter(StatusReporter):

    @classmethod
    def get_status(cls) -> ServiceObservations:
        """
        Reachable if the service can be reached.
        Responding if the configured table is available.
        """
        so = ServiceObservations(label='audit')
        reachable, responding = so.add_checks('reachable', 'responding')

        try:
            audit_db = AuditService.get_instance()
            table = audit_db.dynamodb_client.Table(os.getenv('AUDIT_TABLE'))

            # LocalStack checks
            # Getting table_status triggers an actual connection attempt
            table_status = table.table_status
            reachable.category = Category.success

            if table_status != 'INACCESSIBLE_ENCRYPTION_CREDENTIALS':
                responding.category = Category.success
        except ClientError as ce:
            # Deployed service will give a permission error
            if ce.response['Error']['Code'] == 'AccessDeniedException':
                reachable.category = Category.success
                responding.category = Category.success
            else:
                logger.error(f'Status check {cls.label} unexpected response: {ce.__class__.__name__} {ce}')
        except Exception as e:
            logger.error(f'Status check {cls.label} failed: {e.__class__.__name__} {e}')

        return so

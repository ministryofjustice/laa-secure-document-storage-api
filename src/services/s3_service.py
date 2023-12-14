import boto3

class S3Service:
    _instance = None

    def __init__(self):
        if S3Service._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            S3Service._instance = self
            self._s3_client = boto3.client('s3', region_name='us-east-1',
                                           endpoint_url="http://localhost:4566")

    @staticmethod
    def getInstance():
        if S3Service._instance is None:
            S3Service()
        return S3Service._instance

    def __call__(self):
        return self._s3_client
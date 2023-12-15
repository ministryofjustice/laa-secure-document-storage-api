import boto3
import pytest
from fastapi.testclient import TestClient
from testcontainers.localstack import LocalStackContainer

from src.main import app

client = TestClient(app)

@pytest.fixture(scope="session")
def localstack_container():
    with (LocalStackContainer(image="localstack/localstack:3.0").with_services("s3") as localstack):
        localstack_url = localstack.get_url()
        s3_client = boto3.client(
            's3',
            endpoint_url=localstack_url,
            region_name='us-east-1'
        )

        # Create an S3 bucket
        bucket_name = 'ss-poc-test'
        s3_client.create_bucket(Bucket=bucket_name)

        yield localstack

@pytest.fixture
def localstack_env(monkeypatch, localstack_container):
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("AWS_ENDPOINT_URL", localstack_container.get_url())
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    yield


def test_upload_file(localstack_container, localstack_env):
    response = client.post("/files", files={"file": ("testfile.txt", b"dummy content", "text/plain")},
                           data={"name": "dummy_file_1", "reference": "12345"})
    assert response.status_code == 201
    assert response.json()["file_name"] == "dummy_file_1"


def test_upload_file_without_name(localstack_container):
    response = client.post("/files", files={"file": ("testfile.txt", b"dummy content", "text/plain")},
                           data={"reference": "12345"})
    assert response.status_code == 422
    error_detail = response.json()['detail'][0]
    assert error_detail['loc'][-1] == 'name'
    assert error_detail['msg'] == 'Field required'


def test_upload_file_without_file_and_name(localstack_container):
    response = client.post("/files", data={"reference": "12345"})
    assert response.status_code == 422
    assert response.status_code == 422
    error_detail = response.json()['detail'][0]
    assert error_detail['loc'][-1] == 'file'
    assert error_detail['msg'] == 'Field required'
    error_detail = response.json()['detail'][1]
    assert error_detail['loc'][-1] == 'name'
    assert error_detail['msg'] == 'Field required'


def test_upload_file_without_reference(localstack_container):
    response = client.post("/files", files={"file": ("testfile.txt", b"dummy content", "text/plain")},
                           data={"name": "dummy_file_1"})
    assert response.status_code == 201
    assert response.json()["file_name"] == "dummy_file_1"
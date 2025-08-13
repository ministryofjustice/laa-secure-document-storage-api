from src.models.file_validator_spec import FileValidatorSpec
# test_client is fixture found in test/fixtures/auth.py


def test_available_validators_status_code(test_client):
    response = test_client.get("/available_validators")
    assert response.status_code == 200


def test_available_validators_data_format(test_client):
    response = test_client.get("/available_validators")
    validator_details = response.json()
    validator_details = validator_details
    # No assert as test fails with ValidationError if model_validate fails below
    _ = [FileValidatorSpec.model_validate(v) for v in validator_details]

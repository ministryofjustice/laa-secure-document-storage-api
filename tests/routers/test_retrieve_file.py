import pytest
from src.routers.retrieve_file import app


class TestRetrieveFileEndpoint:
    @pytest.mark.usefixtures("mocker")
    def test_retrieve_file_success(self, mocker):
        mocker.patch('src.routers.retrieve_file.retrieveFileUrl', return_value='https://example.com/test_file')
        response = app.test_client().get('/retrieve_file?file_name=test_file')
        data = response.get_json()
        assert response.status_code == 200
        assert 'fileURL' in data
        assert data['fileURL'] == 'https://example.com/test_file'

    def test_retrieve_file_missing_key(self):
        response = app.test_client().get('/retrieve_file')
        data = response.get_json()
        assert response.status_code == 400
        assert 'error' in data
        assert data['error'] == 'File key is missing'

    @pytest.mark.usefixtures("mocker")
    def test_retrieve_file_error(self, mocker):
        mocker.patch('src.routers.retrieve_file.retrieveFileUrl', side_effect=Exception('Test error'))
        response = app.test_client().get('/retrieve_file?file_name=test_file')
        data = response.get_json()
        assert response.status_code == 500
        assert 'error' in data
        assert data['error'] == 'Test error'

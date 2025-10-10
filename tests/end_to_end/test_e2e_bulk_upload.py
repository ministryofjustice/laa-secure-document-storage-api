import pytest
# Using `as client`, so can easily switch between httpx and requests
import httpx as client
from tests.end_to_end.e2e_helpers import UploadFileData
from tests.end_to_end.e2e_helpers import get_token_manager
from tests.end_to_end.e2e_helpers import get_host_url
from tests.end_to_end.e2e_helpers import get_upload_body
# from tests.end_to_end.e2e_helpers import make_unique_name
# from tests.end_to_end.e2e_helpers import post_a_file
from tests.end_to_end.e2e_helpers import LocalS3


HOST_URL = get_host_url()
UPLOAD_BODY = get_upload_body()
token_getter = get_token_manager()
# Set to return genuine S3 responses when HOST is local ("http://127.0.0.1:8000")
# otherwise s3_client.check_file_exists returns a mock value. This is to save on
# having to set S3 credentials for every environment.
if HOST_URL == "http://127.0.0.1:8000":
    s3_client = LocalS3(mocking_enabled=False)
else:
    s3_client = LocalS3(mocking_enabled=True)


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_test_files():
    """
    Pre-test setup and post-test teardown for tests within this module (file) only.
    Makes standard upload files available to each test and closes them afterwards.
    Code before the "yield" is executed before the tests.
    Code after the "yield" is exected after the last test.
    """
    global test_md_file
    test_md_file = UploadFileData("Postman/test_file.md")
    yield
    test_md_file.close_file()


@pytest.mark.e2e
def test_bulk_upload_works_with_files_payload_example():
    """
    This test is to give a clear example of how the files parameter is constructed for
    multi-file load, avoiding helper functions that hide this away.
    Also shows that the mimetype ('text/plain' here) is optional as it's not included
    in the third file's data.
    """

    files = [('files', ('file1.txt', open('Postman/test_file.md', 'rb'), 'text/plain')),
             ('files', ('file2.txt', open('Postman/test_file.md', 'rb'), 'text/plain')),
             ('files', ('file3.txt', open('Postman/test_file.md', 'rb')))
             ]

    response = client.put(f"{HOST_URL}/bulk_upload",
                          headers=token_getter.get_headers(),
                          files=files,
                          data=UPLOAD_BODY)

    # Two types of expected success - 201 on initial save, 200 on update
    # Both included to cater for re-runs as this is a simple example with fixed filenames
    expected_checksum = "718546961bb3d07169b89bc75c8775b605239bc7189ea0fb92eefc233228804a"
    successful_outcomes = [
        # Save result
        {'file1.txt': {"filename": "file1.txt", "positions": [0], "checksum": expected_checksum, "outcomes": [201]},
         'file2.txt': {"filename": "file2.txt", "positions": [1], "checksum": expected_checksum, "outcomes": [201]},
         'file3.txt': {"filename": "file3.txt", "positions": [2], "checksum": expected_checksum, "outcomes": [201]}},
        # Update result
        {'file1.txt': {"filename": "file1.txt", "positions": [0], "checksum": expected_checksum, "outcomes": [200]},
         'file2.txt': {"filename": "file2.txt", "positions": [1], "checksum": expected_checksum, "outcomes": [200]},
         'file3.txt': {"filename": "file3.txt", "positions": [2], "checksum": expected_checksum, "outcomes": [200]}
         }
        ]
    assert response.status_code == 200
    assert response.json() in successful_outcomes

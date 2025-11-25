import pytest
# Using `as client`, so can easily switch between httpx and requests
import httpx as client
from tests.end_to_end.e2e_helpers import UploadFileData
from tests.end_to_end.e2e_helpers import get_token_manager
from tests.end_to_end.e2e_helpers import get_host_url
from tests.end_to_end.e2e_helpers import get_upload_body
from tests.end_to_end.e2e_helpers import make_unique_name
# from tests.end_to_end.e2e_helpers import post_a_file
from tests.end_to_end.e2e_helpers import LocalS3, AuditDynamoDBClient


HOST_URL = get_host_url()
UPLOAD_BODY = get_upload_body()
token_getter = get_token_manager()
# Set to return genuine S3 responses when HOST is local ("http://127.0.0.1:8000")
# otherwise s3_client.check_file_exists returns a mock value. This is to save on
# having to set S3 credentials for every environment.
if HOST_URL == "http://127.0.0.1:8000":
    s3_client = LocalS3(mocking_enabled=False)
    audit_table_client = AuditDynamoDBClient(mocking_enabled=False)
else:
    s3_client = LocalS3(mocking_enabled=True)
    audit_table_client = AuditDynamoDBClient(mocking_enabled=True)


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_test_files():
    """
    Pre-test setup and post-test teardown for tests within this module (file) only.
    Makes standard upload files available to each test and closes them afterwards.
    Code before the "yield" is executed before the tests.
    Code after the "yield" is exected after the last test.
    """
    global test_md_file, test_md_file2, virus_file, disallowed_file
    test_md_file = UploadFileData("Postman/test_file.md")
    test_md_file2 = UploadFileData("Postman/test_file2.md")
    virus_file = UploadFileData("Postman/eicar.txt")
    disallowed_file = UploadFileData("Postman/test_file.exe")
    yield
    test_md_file.close_file()
    test_md_file2.close_file()
    virus_file.close_file()
    disallowed_file.close_file()


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

    # "saved" and "updated" outcomes - short variable names to keep line lengths below 119 chars
    os = {"status_code": 201, "detail": "saved"}
    ou = {"status_code": 200, "detail": "updated"}

    successful_outcomes = [
        # Saved result
        {'file1.txt': {"filename": "file1.txt", "positions": [0], "checksum": expected_checksum, "outcomes": [os]},
         'file2.txt': {"filename": "file2.txt", "positions": [1], "checksum": expected_checksum, "outcomes": [os]},
         'file3.txt': {"filename": "file3.txt", "positions": [2], "checksum": expected_checksum, "outcomes": [os]}},
        # Updated result
        {'file1.txt': {"filename": "file1.txt", "positions": [0], "checksum": expected_checksum, "outcomes": [ou]},
         'file2.txt': {"filename": "file2.txt", "positions": [1], "checksum": expected_checksum, "outcomes": [ou]},
         'file3.txt': {"filename": "file3.txt", "positions": [2], "checksum": expected_checksum, "outcomes": [ou]}}
        ]
    assert response.status_code == 200
    assert response.json() in successful_outcomes
    # Audit table update check - CREATE or UPDATE accepted to allow for re-runs
    if audit_table_client.mocking_enabled is False:
        # File 1
        audit_item_0 = audit_table_client.get_audit_row_e2e(response, 0)
        assert audit_item_0.get("file_id") == {'S': "file1.txt"}
        assert audit_item_0.get("operation_type") in [{'S': 'CREATE'}, {'S': 'UPDATE'}]
        assert audit_item_0.get("error_details") == {'S': ''}
        # File 2
        audit_item_1 = audit_table_client.get_audit_row_e2e(response, 1)
        assert audit_item_1.get("file_id") == {'S': "file2.txt"}
        assert audit_item_1.get("operation_type") in [{'S': 'CREATE'}, {'S': 'UPDATE'}]
        assert audit_item_1.get("error_details") == {'S': ''}
        audit_item_2 = audit_table_client.get_audit_row_e2e(response, 2)
        # File 3
        assert audit_item_2.get("file_id") == {'S': "file3.txt"}
        assert audit_item_2.get("operation_type") in [{'S': 'CREATE'}, {'S': 'UPDATE'}]
        assert audit_item_2.get("error_details") == {'S': ''}


@pytest.mark.e2e
@pytest.mark.parametrize("file_count", [1, 2, 4, 8, 64])
def test_bulk_upload_multiple_files_with_different_filenames(file_count):
    expected_checksum = "718546961bb3d07169b89bc75c8775b605239bc7189ea0fb92eefc233228804a"
    files = []
    expected_result = {}
    for i in range(file_count):
        # Construct files payload
        new_filename = make_unique_name("test.txt")
        files.append(('files', (new_filename, open('Postman/test_file.md', 'rb'), 'text/plain')))
        # Add expected result
        expected_result[new_filename] = {"filename": new_filename,
                                         "positions": [i], "checksum": expected_checksum,
                                         "outcomes": [{"status_code": 201, "detail": "saved"}]}

    response = client.put(f"{HOST_URL}/bulk_upload",
                          headers=token_getter.get_headers(),
                          files=files,
                          data=UPLOAD_BODY)

    assert response.status_code == 200
    assert response.json() == expected_result


# This one was troublesome to setup - care needed to get expected result right
@pytest.mark.e2e
@pytest.mark.parametrize("file_count", [1, 2, 4, 8, 64])
def test_bulk_upload_same_filename_multiple_times(file_count):
    # Construct files payload
    new_filename = make_unique_name("test.txt")
    files = [('files', (new_filename, open('Postman/test_file.md', 'rb'), 'text/plain'))] * file_count
    # Construct expected result - one filename with mulitple outcomes
    expected_checksum = "718546961bb3d07169b89bc75c8775b605239bc7189ea0fb92eefc233228804a"
    expected_outcomes = [{"status_code": 201, "detail": "saved"}] + \
        [{"status_code": 200, "detail": "updated"}] * (file_count-1)
    expected_result = {new_filename: {"filename": new_filename,
                                      "positions": list(range(file_count)),
                                      "outcomes": expected_outcomes,
                                      "checksum": expected_checksum
                                      }
                       }

    response = client.put(f"{HOST_URL}/bulk_upload",
                          headers=token_getter.get_headers(),
                          files=files,
                          data=UPLOAD_BODY)

    assert response.status_code == 200
    assert response.json() == expected_result


@pytest.mark.e2e
def test_bulk_upload_with_multiple_versions_of_same_file_gives_checksum_from_the_last():
    """
    This test is to check that when the same filename is loaded more than once, the checksum
    returned is that of the last file to be saved. (The test above could not do this because
    all the files have the same checksum)
    """
    # Make 3 files with same filename but third has different content, and so different checksum
    new_filename = make_unique_name("checksumtest.txt")
    files = [
        test_md_file.get_data_tuple(new_filename),
        test_md_file.get_data_tuple(new_filename),
        test_md_file2.get_data_tuple(new_filename)
        ]
    expected_outcomes = [{"status_code": 201, "detail": "saved"},
                         {"status_code": 200, "detail": "updated"},
                         {"status_code": 200, "detail": "updated"}]
    # Checksum for test_md_file2 (which is different from that of test_md_file)
    expected_checksum = "448061d26023c5d17c15ba9cc73635c457a071b25ab4a773e2a276a85abf2d8f"

    response = client.put(f"{HOST_URL}/bulk_upload",
                          headers=token_getter.get_headers(),
                          files=files,
                          data=UPLOAD_BODY)

    assert response.status_code == 200
    assert response.json() == {new_filename: {"filename": new_filename,
                                              "positions": [0, 1, 2],
                                              "outcomes": expected_outcomes,
                                              "checksum": expected_checksum}
                               }


@pytest.mark.e2e
def test_bulk_upload_gives_expected_error_when_no_files_supplied():
    response = client.put(f"{HOST_URL}/bulk_upload",
                          headers=token_getter.get_headers(),
                          files=[],
                          data=UPLOAD_BODY)

    expected_error = '{"detail":[{"type":"missing","loc":["body","files"],"msg":"Field required","input":null}]}'
    assert response.status_code == 422
    assert response.text == expected_error


@pytest.mark.e2e
def test_bulk_upload_with_invalid_files_returns_expected_errors():
    expected_checksum = '718546961bb3d07169b89bc75c8775b605239bc7189ea0fb92eefc233228804a'
    good_file1 = make_unique_name("good_file.txt")
    good_file2 = make_unique_name("good_file.txt")
    files = [
        test_md_file.get_data_tuple(good_file1),  # Valid file
        virus_file.get_data_tuple("virus_file.txt"),  # Virus
        disallowed_file.get_data_tuple("bad_type.exe"),  # Bad mimetype
        test_md_file.get_data_tuple("..."),  # Bad filename - extension unclear
        test_md_file.get_data_tuple("bad_char|.txt"),  # Bad filename - contains forbidden character
        test_md_file.get_data_tuple(good_file2),  # Another valid file
        ]
    response = client.put(f"{HOST_URL}/bulk_upload",
                          headers=token_getter.get_headers(),
                          files=files,
                          data=UPLOAD_BODY)

    response_details = response.json()
    assert response.status_code == 200
    # Asserting the whole result in one go would be a bit much - file-by-file easier to maintain
    assert response_details[good_file1] == {'filename': good_file1,
                                            'positions': [0],
                                            'outcomes': [{'status_code': 201, 'detail': 'saved'}],
                                            'checksum': expected_checksum}
    assert response_details["virus_file.txt"] == {'filename': 'virus_file.txt',
                                                  'positions': [1],
                                                  'outcomes': [{'status_code': 400, 'detail': ['Virus Found']}],
                                                  'checksum': None}  # likely auto-convert of json null to Python None
    assert response_details["bad_type.exe"] == {'filename': 'bad_type.exe',
                                                'positions': [2],
                                                'outcomes': [{'status_code': 415,
                                                              'detail': 'File mimetype not allowed'}],
                                                'checksum': None}  # likely auto-convert of json null to Python None
    assert response_details["..."] == {'filename': '...',
                                       'positions': [3],
                                       'outcomes': [{'status_code': 415, 'detail': 'File extension not allowed'}],
                                       'checksum': None}
    assert response_details["bad_char|.txt"] == {'filename': 'bad_char|.txt',
                                                 'positions': [4],
                                                 'outcomes': [{'status_code': 400, 'detail':
                                                              'Filename contains characters that are not allowed'}],
                                                 'checksum': None}
    assert response_details[good_file2] == {'filename': good_file2,
                                            'positions': [5],
                                            'outcomes': [{'status_code': 201, 'detail': 'saved'}],
                                            'checksum': expected_checksum}
    # Check right number of results
    assert len(response_details) == len(files)

    # Audit table check
    if audit_table_client.mocking_enabled is False:
        # Good file
        audit_item_0 = audit_table_client.get_audit_row_e2e(response, 0)
        assert audit_item_0.get("file_id") == {'S': good_file1}
        assert audit_item_0.get("operation_type") == {'S': 'CREATE'}
        assert audit_item_0.get("error_details") == {'S': ''}
        # Virus file
        audit_item_1 = audit_table_client.get_audit_row_e2e(response, 1)
        assert audit_item_1.get("file_id") == {'S': "virus_file.txt"}
        assert audit_item_1.get("operation_type") == {'S': 'FAILED'}
        assert audit_item_1.get("error_details") == {'S': f"{response.url}: ['Virus Found']"}
        # Bad mimetype
        audit_item_2 = audit_table_client.get_audit_row_e2e(response, 2)
        assert audit_item_2.get("file_id") == {'S': "bad_type.exe"}
        assert audit_item_2.get("operation_type") == {'S': 'FAILED'}
        assert audit_item_2.get("error_details") == {'S': f'{response.url}: File mimetype not allowed'}
        # Bad file extension
        audit_item_3 = audit_table_client.get_audit_row_e2e(response, 3)
        assert audit_item_3.get("file_id") == {'S': "..."}
        assert audit_item_3.get("operation_type") == {'S': 'FAILED'}
        assert audit_item_3.get("error_details") == {'S': f'{response.url}: File extension not allowed'}
        # Bad character in filename
        audit_item_4 = audit_table_client.get_audit_row_e2e(response, 4)
        assert audit_item_4.get("file_id") == {'S': "bad_char|.txt"}
        assert audit_item_4.get("operation_type") == {'S': 'FAILED'}
        assert audit_item_4.get("error_details") == {'S': f'{response.url}'
                                                     ': Filename contains characters that are not allowed'}
        # Another good file
        audit_item_5 = audit_table_client.get_audit_row_e2e(response, 5)
        assert audit_item_5.get("file_id") == {'S': good_file2}
        assert audit_item_5.get("operation_type") == {'S': 'CREATE'}
        assert audit_item_5.get("error_details") == {'S': ''}

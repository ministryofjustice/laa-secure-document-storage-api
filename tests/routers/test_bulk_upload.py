from unittest.mock import patch
from io import BytesIO
import pytest
from fastapi import HTTPException
from src.models.file_upload import UploadFileResponse
# test_client is fixture auto-imported from tests/fixtures/auth.py


def make_file_tuple(filename: str, content: bytes = b"abc123", mimetype: str = "text/plain"):
    "Create tuple with individual file details for upload"
    return ("files", (filename, BytesIO(content), mimetype))


def make_file_result(filename: str, positions: list[int], outcomes: list[dict], checksum: str | None):
    "Create file result dict"
    return {"filename": filename, "positions": positions, "outcomes": outcomes, "checksum": checksum}


# =========================== SUCCESS =========================== #

good_save_response = UploadFileResponse(success="File saved successfully in test_bucket with key test_file.txt",
                                        checksum="ABC123", version_id="1000000", file_already_existed=False)

good_update_response_1 = UploadFileResponse(success="File updated successfully in test_bucket with key test_file.txt",
                                            checksum="DEF456", version_id="2000000", file_already_existed=True)

good_update_response_2 = UploadFileResponse(success="File updated successfully in test_bucket with key test_file.txt",
                                            checksum="GHI789", version_id="3000000", file_already_existed=True)


@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_with_one_file(mock_handler, test_client):
    mock_handler.return_value = good_save_response

    files = [("files", ("test_file.txt", BytesIO(b"Test content"), "text/plain"))]
    response = test_client.put("/bulk_upload", files=files)

    assert response.status_code == 200
    assert response.json() == {'test_file.txt': {'filename': 'test_file.txt',
                                                 'positions': [0],
                                                 'outcomes': [{'status_code': 201,
                                                               'detail': 'saved',
                                                               'version_id': '1000000'}],
                                                 'checksum': 'ABC123'}}


@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_with_same_filename_thrice(mock_handler, test_client):
    # Upload details
    files = [make_file_tuple("test.txt", b"file1"),
             make_file_tuple("test.txt", b"file2"),
             make_file_tuple("test.txt", b"file3")]
    # Mock handler side effect for the 3 files in sequence
    mock_handler.side_effect = [good_save_response, good_update_response_1, good_update_response_2]
    # Expected result
    expected_result = {"test.txt": {"filename": "test.txt",
                                    "positions": [0, 1, 2],
                                    "outcomes": [{"status_code": 201, "detail": "saved", "version_id": "1000000"},
                                                 {"status_code": 200, "detail": "updated", "version_id": "2000000"},
                                                 {"status_code": 200, "detail": "updated",  "version_id": "3000000"}],
                                    "checksum": "GHI789"  # Expect value from last file
                                    }}
    # Make request
    response = test_client.put("/bulk_upload", files=files)

    assert response.status_code == 200
    assert response.json() == expected_result


# File load with different numbers of files and no repeat filenames within each load
# Asumption each run is unique, so always 201 "saved" - "no updates"
# Care with decorator ordering and param positions
@pytest.mark.parametrize("file_count", [1, 10, 100, 1000])
@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_with_multiple_files(mock_handler, file_count, test_client):
    # Make files payload
    filenames = [f"file{n}.txt" for n in range(file_count)]
    # f.encode() is simple way of making unique bytes content for each file
    files = [make_file_tuple(f, f.encode()) for f in filenames]

    # Make (i) related side-effect for mock handler and (ii) expected result
    # for each file in the load
    side_effect = []
    expected_result = {}
    for fi, filename in enumerate(filenames):
        checksum = f"fakechecksum{fi}"
        version_id = f"version-{fi}"
        # for mock handler response
        message = f"File saved successfully in test_bucket with key {filename}"
        updated = False
        # For expected result
        status_code = 201
        detail = "saved"

        # Construct mock handler responses for each file
        mock_handler_response = UploadFileResponse(success=message,
                                                   checksum=checksum,
                                                   version_id=version_id,
                                                   file_already_existed=updated)
        side_effect.append(mock_handler_response)

        # Add expected bulk upload result for each file
        expected_result[filename] = {"filename": filename,
                                     "positions": [fi],
                                     "outcomes": [{'status_code': status_code,
                                                   'detail': detail,
                                                   'version_id': version_id}],
                                     "checksum": checksum
                                     }
    mock_handler.side_effect = side_effect

    # Make request
    response = test_client.put("/bulk_upload", files=files)

    # "headline" status code always 200 but individual file outcomes have 201 here
    assert response.status_code == 200
    assert response.json() == expected_result
    assert len(response.json()) == file_count


@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_with_both_repeated_and_different_filenames(mock_handler, test_client):
    # Upload details - unique filenames start "u", repeated start "r"
    files = [make_file_tuple("ufile1.txt", b"file1"),
             make_file_tuple("ufile2.txt", b"file2"),
             make_file_tuple("ufile3.txt", b"file3"),
             make_file_tuple("rfile1.txt", b"file4"),
             make_file_tuple("ufile4.txt", b"file5"),
             make_file_tuple("rfile1.txt", b"file6")  # repeated filename
             ]
    # Mock handler side effect
    handle1 = UploadFileResponse(success="File saved successfully in test_bucket with key ufile1.txt",
                                 checksum="fakechecksum1",
                                 version_id="1",
                                 file_already_existed=False)
    handle2 = UploadFileResponse(success="File saved successfully in test_bucket with key ufile2.txt",
                                 checksum="fakechecksum2",
                                 version_id="2",
                                 file_already_existed=False)
    handle3 = UploadFileResponse(success="File saved successfully in test_bucket with key ufile3.txt",
                                 checksum="fakechecksum3",
                                 version_id="3",
                                 file_already_existed=False)
    handle4 = UploadFileResponse(success="File saved successfully in test_bucket with key rfile1.txt",
                                 checksum="fakechecksum4",
                                 version_id="4",
                                 file_already_existed=False)
    handle5 = UploadFileResponse(success="File saved successfully in test_bucket with key ufile4.txt",
                                 checksum="fakechecksum5",
                                 version_id="5",
                                 file_already_existed=False)
    handle6 = UploadFileResponse(success="File updated successfully in test_bucket with key rfile1.txt",
                                 checksum="fakechecksum6",
                                 version_id="6",
                                 file_already_existed=True)
    mock_handler.side_effect = [handle1, handle2, handle3, handle4, handle5, handle6]

    # Expected result - repeated file, rfile1.txt, only has checksum from its final load (fakechecksum6)
    expected_result = {}
    expected_result["ufile1.txt"] = make_file_result(
        "ufile1.txt", [0], [{"status_code": 201, "detail": "saved", "version_id": "1"}], "fakechecksum1")
    expected_result["ufile2.txt"] = make_file_result(
        "ufile2.txt", [1], [{"status_code": 201, "detail": "saved", "version_id": "2"}], "fakechecksum2")
    expected_result["ufile3.txt"] = make_file_result(
        "ufile3.txt", [2], [{"status_code": 201, "detail": "saved", "version_id": "3"}], "fakechecksum3")
    expected_result["rfile1.txt"] = make_file_result("rfile1.txt", [3, 5],
                                                     [{"status_code": 201, "detail": "saved", "version_id": "4"},
                                                     {"status_code": 200, "detail": "updated", "version_id": "6"}],
                                                     "fakechecksum6")
    expected_result["ufile4.txt"] = make_file_result(
        "ufile4.txt", [4], [{"status_code": 201, "detail": "saved", "version_id": "5"}], "fakechecksum5")

    # Make request
    response = test_client.put("/bulk_upload", files=files)

    assert response.status_code == 200
    assert response.json() == expected_result


# ================== Request Body (data param) ================== #
"""
In earlier version of API it was necessary to specify a `bucketName` value
in the request body but this is no longer the case. Body is now optional and
only used to specify optional folder value.
(When making request body is specified using data parameter)
"""


@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_with_no_body_processed_successfully(mock_handler, test_client):
    mock_handler.return_value = good_save_response

    files = [("files", ("test_file.txt", BytesIO(b"Test content"), "text/plain"))]
    response = test_client.put("/bulk_upload", files=files)

    assert response.status_code == 200
    assert response.json() == {'test_file.txt': {'filename': 'test_file.txt',
                                                 'positions': [0],
                                                 'outcomes': [{'status_code': 201,
                                                               'detail': 'saved',
                                                               'version_id': "1000000"}],
                                                 'checksum': 'ABC123'}}


@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_with_body_folder_value_processed_successfully(mock_handler, test_client):
    # Due to mocked return value we can't see if specified folder has been used from response
    # but can assert if folder included in FileUpload object passed to  mock handler.
    mock_handler.return_value = good_save_response

    data = {"body": '{"folder": "test_folder"}'}

    files = [("files", ("test_file.txt", BytesIO(b"Test content"), "text/plain"))]
    response = test_client.put("/bulk_upload", data=data, files=files)

    assert response.status_code == 200
    assert response.json() == {'test_file.txt': {'filename': 'test_file.txt',
                                                 'positions': [0],
                                                 'outcomes': [{'status_code': 201,
                                                               'detail': 'saved',
                                                               'version_id': "1000000"}],
                                                 'checksum': 'ABC123'}}
    # Check that the folder specified in request body has been forwarded to file handler in FileUpload object
    # Note will likley need updating if FileUpload model has new attributes
    assert "FileUpload(folder='test_folder')" in str(mock_handler.call_args)


# Body has syntactically correct json but data is irrelevant - success result
@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_with_body_with_irrelevant_body_content_processed_successfully(mock_handler, test_client):
    mock_handler.return_value = good_save_response
    # Details below are not relevant as they do not correspond with FileUpload model
    data = {"body": '{"bucketName": "test_bucket", "speed": "extra fast"}'}

    files = [("files", ("test_file.txt", BytesIO(b"Test content"), "text/plain"))]
    response = test_client.put("/bulk_upload", data=data, files=files)

    assert response.status_code == 200
    assert response.json() == {'test_file.txt': {'filename': 'test_file.txt',
                                                 'positions': [0],
                                                 'outcomes': [{'status_code': 201,
                                                               'detail': 'saved',
                                                               'version_id': "1000000"}],
                                                 'checksum': 'ABC123'}}


# Body contains invalid json - fail result
@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_gives_expected_error_when_body_not_valid(mock_handler, test_client):
    data = {"body": "bad body"}
    files = [("files", ("test_file.txt", BytesIO(b"Test content"), "text/plain"))]

    response = test_client.put("/bulk_upload",  data=data, files=files)

    assert response.status_code == 400
    assert response.json() == {'detail': {'': 'Invalid JSON: expected value at line 1 column 1'}}
    mock_handler.assert_not_called()


# ====================== FAILURE (general) ====================== #

@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_gives_expected_error_when_no_files(mock_handler, test_client):
    files = []

    response = test_client.put("/bulk_upload", files=files)

    assert response.status_code == 422
    assert response.json() == {"detail": [{"type": "missing",
                                           "loc": ["body", "files"],
                                           "msg": "Field required",
                                           "input": None}]}
    mock_handler.assert_not_called()


# ====================== FAILURE (per file) ===================== #

@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_gives_expected_errors_when_invalid_files_present(mock_handler, test_client):
    # Make files payload
    files = [make_file_tuple("goodfile1.txt", b"file1"),  # Good file
             make_file_tuple("virusfile.txt", b"file2"),  # Bad file
             make_file_tuple(".............", b"file3"),  # Bad file
             make_file_tuple("goodfile2.txt", b"file4")]  # Good file
    # Mock handler side effect
    handle1 = UploadFileResponse(success="File saved successfully in test_bucket with key goodfile1.txt",
                                 checksum="fakechecksum1", version_id="1000000", file_already_existed=False)
    handle2 = HTTPException(status_code=400, detail="Virus Found")
    handle3 = HTTPException(status_code=415, detail="File extension not allowed")
    handle4 = UploadFileResponse(success="File saved successfully in test_bucket with key goodfile2.txt",
                                 checksum="fakechecksum2", version_id="2000000", file_already_existed=False)
    mock_handler.side_effect = [handle1, handle2, handle3, handle4]

    # Expected Result
    expected_result = {}
    expected_result["goodfile1.txt"] = make_file_result("goodfile1.txt", [0],
                                                        [{"status_code": 201,
                                                          "detail": "saved",
                                                          "version_id": "1000000"}],
                                                        "fakechecksum1")
    expected_result["virusfile.txt"] = make_file_result("virusfile.txt", [1],
                                                        [{'status_code': 400, 'detail': 'Virus Found'}],
                                                        None)
    expected_result["............."] = make_file_result(".............", [2],
                                                        [{'status_code': 415,
                                                          'detail': 'File extension not allowed'}],
                                                        None)
    expected_result["goodfile2.txt"] = make_file_result("goodfile2.txt", [3],
                                                        [{"status_code": 201,
                                                          "detail": "saved",
                                                          "version_id": "2000000"}],
                                                        "fakechecksum2")

    response = test_client.put("/bulk_upload", files=files)
    assert response.status_code == 200
    assert response.json() == expected_result

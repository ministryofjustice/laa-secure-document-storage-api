from unittest.mock import patch
from io import BytesIO
import pytest
from fastapi import HTTPException
# test_client is fixture auto-imported from tests/fixtures/auth.py


def make_file_tuple(filename: str, content: bytes = b"abc123", mimetype: str = "text/plain"):
    "Create tuple with individual file details for upload"
    return ("files", (filename, BytesIO(content), mimetype))


def make_file_result(filename: str, positions: list[int], outcomes: list[dict], checksum: str | None):
    "Create file result dict"
    return {"filename": filename, "positions": positions, "outcomes": outcomes, "checksum": checksum}


# =========================== SUCCESS =========================== #


@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_with_one_file(mock_handler, test_client):
    mock_handler.return_value = (
        {"success": "File saved successfully in test_bucket with key test_file.txt",
         "checksum": "fakechecksum123"},
        False
        )

    data = {"body": '{"bucketName": "test_bucket"}'}
    files = [("files", ("test_file.txt", BytesIO(b"Test content"), "text/plain"))]
    response = test_client.put("/bulk_upload",  data=data, files=files)

    assert response.status_code == 200
    assert response.json() == {'test_file.txt': {'filename': 'test_file.txt',
                                                 'positions': [0],
                                                 'outcomes': [{'status_code': 201, 'detail': 'saved'}],
                                                 'checksum': 'fakechecksum123'}}


@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_with_same_filename_thrice(mock_handler, test_client):
    # Upload details
    data = {"body": '{"bucketName": "test_bucket"}'}
    files = [make_file_tuple("test.txt", b"file1"),
             make_file_tuple("test.txt", b"file2"),
             make_file_tuple("test.txt", b"file3")]
    # Mock handler side effect
    handle1 = {"success": "File saved successfully in test_bucket with key test.txt",
               "checksum": "fakechecksum1"}
    handle2 = {"success": "File updated successfully in test_bucket with key test.txt",
               "checksum": "fakechecksum2"}
    handle3 = {"success": "File updated successfully in test_bucket with key test.txt",
               "checksum": "fakechecksum3"}
    mock_handler.side_effect = [(handle1, False), (handle2, True), (handle3, True)]
    # Expected result
    expected_result = {"test.txt": {"filename": "test.txt",
                                    "positions": [0, 1, 2],
                                    "outcomes": [{"status_code": 201, "detail": "saved"},
                                                 {"status_code": 200, "detail": "updated"},
                                                 {"status_code": 200, "detail": "updated"}],
                                    "checksum": "fakechecksum3"  # Expect value from last file
                                    }}
    # Make request
    response = test_client.put("/bulk_upload",  data=data, files=files)

    assert response.status_code == 200
    assert response.json() == expected_result


# Care with decorator ordering and param positions
@pytest.mark.parametrize("file_count", [1, 10, 100, 1000])
@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_with_multiple_files(mock_handler, file_count, test_client):
    data = {"body": '{"bucketName": "test_bucket"}'}

    # Make files payload
    filenames = [f"file{n}.txt" for n in range(file_count)]
    # f.encode() is simple way of making unique bytes content for each file
    files = [make_file_tuple(f, f.encode()) for f in filenames]

    # Make (i) related side-effect for mock handler and (ii) expected result
    side_effect = []
    expected_result = {}
    for fi, filename in enumerate(filenames):
        checksum = f"fakechecksum{fi}"
        se_item = {"success": f"File saved successfully in test_bucket with key {filename}",
                   "checksum": checksum}
        side_effect.append((se_item, False))
        expected_result[filename] = {"filename": filename,
                                     "positions": [fi],
                                     "outcomes": [{'status_code': 201, 'detail': 'saved'}],
                                     "checksum": checksum
                                     }
    mock_handler.side_effect = side_effect

    # Make request
    response = test_client.put("/bulk_upload",  data=data, files=files)

    assert response.status_code == 200
    assert response.json() == expected_result
    assert len(response.json()) == file_count


@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_with_both_repeated_and_different_filenames(mock_handler, test_client):
    # Upload details - unique filenames start "u", repeated start "r"
    data = {"body": '{"bucketName": "test_bucket"}'}
    files = [make_file_tuple("ufile1.txt", b"file1"),
             make_file_tuple("ufile2.txt", b"file2"),
             make_file_tuple("ufile3.txt", b"file3"),
             make_file_tuple("rfile1.txt", b"file4"),
             make_file_tuple("ufile4.txt", b"file5"),
             make_file_tuple("rfile1.txt", b"file6")
             ]
    # Mock handler side effect
    handle1 = {"success": "File saved successfully in test_bucket with key ufile1.txt",
               "checksum": "fakechecksum1"}
    handle2 = {"success": "File saved successfully in test_bucket with key ufile2.txt",
               "checksum": "fakechecksum2"}
    handle3 = {"success": "File saved successfully in test_bucket with key ufile3.txt",
               "checksum": "fakechecksum3"}
    handle4 = {"success": "File saved successfully in test_bucket with key rfile1.txt",
               "checksum": "fakechecksum4"}
    handle5 = {"success": "File saved successfully in test_bucket with key ufile4.txt",
               "checksum": "fakechecksum5"}
    handle6 = {"success": "File updated successfully in test_bucket with key rfile1.txt",
               "checksum": "fakechecksum6"}
    mock_handler.side_effect = [(handle1, False), (handle2, False), (handle3, False),
                                (handle4, False), (handle5, False), (handle6, True)]
    # Expected result
    saved_outcome = {"status_code": 201, "detail": "saved"}
    updated_outcome = {"status_code": 200, "detail": "updated"}
    expected_result = {}
    expected_result["ufile1.txt"] = make_file_result("ufile1.txt", [0], [saved_outcome], "fakechecksum1")
    expected_result["ufile2.txt"] = make_file_result("ufile2.txt", [1], [saved_outcome], "fakechecksum2")
    expected_result["ufile3.txt"] = make_file_result("ufile3.txt", [2], [saved_outcome], "fakechecksum3")
    expected_result["rfile1.txt"] = make_file_result("rfile1.txt", [3, 5], [saved_outcome, updated_outcome],
                                                     "fakechecksum6")
    expected_result["ufile4.txt"] = make_file_result("ufile4.txt", [4], [saved_outcome], "fakechecksum5")

    # Make request
    response = test_client.put("/bulk_upload",  data=data, files=files)

    assert response.status_code == 200
    assert response.json() == expected_result


# ====================== FAILURE (general) ====================== #

# "three body problem!" - the 3 tests below have similar data param issues but distinct responses
@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_gives_expected_error_when_data_empty(mock_handler, test_client):
    data = {}
    files = [("files", ("test_file.txt", BytesIO(b"Test content"), "text/plain"))]

    response = test_client.post("/save_file", data=data, files=files)

    assert response.status_code == 422
    assert response.json() == {'detail': [{'input': None,
                                           'loc': ['body', 'body'],
                                           'msg': 'Field required',
                                           'type': 'missing'}]}
    mock_handler.assert_not_called()


@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_gives_expected_error_when_body_not_valid(mock_handler, test_client):
    data = {"body": "bad body"}
    files = [("files", ("test_file.txt", BytesIO(b"Test content"), "text/plain"))]

    response = test_client.put("/bulk_upload",  data=data, files=files)

    assert response.status_code == 400
    assert response.json() == {'detail': {'': 'Invalid JSON: expected value at line 1 column 1'}}
    mock_handler.assert_not_called()


@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_gives_expected_error_when_body_lacks_bucket(mock_handler, test_client):
    data = {"body": "{}"}
    files = [("files", ("test_file.txt", BytesIO(b"Test content"), "text/plain"))]

    response = test_client.put("/bulk_upload",  data=data, files=files)

    assert response.status_code == 400
    assert response.json() == {"detail": {"bucketName": "Field required"}}
    mock_handler.assert_not_called()


@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_gives_expected_error_when_no_files(mock_handler, test_client):
    data = {"body": '{"bucketName": "test_bucket"}'}
    files = []

    response = test_client.put("/bulk_upload",  data=data, files=files)

    assert response.status_code == 422
    assert response.json() == {"detail": [{"type": "missing",
                                           "loc": ["body", "files"],
                                           "msg": "Field required",
                                           "input": None}]}
    mock_handler.assert_not_called()


# ====================== FAILURE (per file) ===================== #

@patch("src.routers.bulk_upload.handle_file_upload_logic")
def test_bulk_upload_gives_expected_errors_when_invalid_files_present(mock_handler, test_client):
    data = {"body": '{"bucketName": "test_bucket"}'}
    # Make files payload
    files = [make_file_tuple("goodfile1.txt", b"file1"),  # Good file
             make_file_tuple("virusfile.txt", b"file2"),  # Bad file
             make_file_tuple(".............", b"file3"),  # Bad file
             make_file_tuple("goodfile2.txt", b"file4")]  # Good file
    # Mock handler side effect
    handle1 = {"success": "File saved successfully in test_bucket with key goodfile1.txt",
               "checksum": "fakechecksum1"}
    handle2 = HTTPException(status_code=400, detail="Virus Found")
    handle3 = HTTPException(status_code=415, detail="File extension not allowed")
    handle4 = {"success": "File saved successfully in test_bucket with key goodfile2.txt",
               "checksum": "fakechecksum2"}
    mock_handler.side_effect = [(handle1, False), handle2, handle3, (handle4, False)]
    # Expected Result
    expected_result = {}
    expected_result["goodfile1.txt"] = make_file_result("goodfile1.txt", [0],
                                                        [{"status_code": 201, "detail": "saved"}],
                                                        "fakechecksum1")
    expected_result["virusfile.txt"] = make_file_result("virusfile.txt", [1],
                                                        [{'status_code': 400, 'detail': 'Virus Found'}],
                                                        None)
    expected_result["............."] = make_file_result(".............", [2],
                                                        [{'status_code': 415,
                                                          'detail': 'File extension not allowed'}],
                                                        None)
    expected_result["goodfile2.txt"] = make_file_result("goodfile2.txt", [3],
                                                        [{"status_code": 201, "detail": "saved"}],
                                                        "fakechecksum2")

    response = test_client.put("/bulk_upload",  data=data, files=files)
    assert response.status_code == 200
    assert response.json() == expected_result

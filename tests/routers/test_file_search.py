from unittest.mock import patch


def test_file_search_success(test_client, audit_service_mock):
    expected_result = {
        "files": [
            "folder/file1.txt",
            "folder/file2.txt",
        ],
        "continuation_token": "next-page",
    }

    with patch(
        "src.routers.file_search.list_file_search",
        return_value=expected_result,
    ):
        response = test_client.get(
            "/file_search",
            params={
                "folder": "folder/",
                "max_keys": 100,
            },
        )

    assert response.status_code == 200
    assert response.json() == expected_result
    audit_service_mock.assert_called()


def test_file_search_success_with_continuation_token(
    test_client,
    audit_service_mock,
):
    expected_result = {
        "files": ["folder/file3.txt"],
        "continuation_token": "page-2",
    }

    with patch(
        "src.routers.file_search.list_file_search",
        return_value=expected_result,
    ):
        response = test_client.get(
            "/file_search",
            params={
                "folder": "folder/",
                "max_keys": 50,
                "continuation_token": "page-1",
            },
        )

    assert response.status_code == 200
    assert response.json() == expected_result
    audit_service_mock.assert_called()


def test_file_search_without_folder(
    test_client,
    audit_service_mock,
):
    expected_result = {
        "files": ["file1.txt", "file2.txt"],
        "continuation_token": None,
    }

    with patch(
        "src.routers.file_search.list_file_search",
        return_value=expected_result,
    ) as mock_search:
        response = test_client.get("/file_search")

    assert response.status_code == 200
    assert response.json() == expected_result

    mock_search.assert_called_once()
    audit_service_mock.assert_called()


def test_file_search_returns_400_when_max_keys_exceeds_limit(
    test_client,
    audit_service_mock,
):
    response = test_client.get(
        "/file_search",
        params={
            "folder": "folder/",
            "max_keys": 1001,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File key is missing"

    audit_service_mock.assert_called()


def test_file_search_returns_500_when_service_raises_exception(
    test_client,
    audit_service_mock,
):
    with patch(
        "src.routers.file_search.list_file_search",
        side_effect=RuntimeError("S3 failure"),
    ):
        response = test_client.get(
            "/file_search",
            params={
                "folder": "folder/",
                "max_keys": 100,
            },
        )

    assert response.status_code == 500
    assert (
        response.json()["detail"]
        == "Unexpected error during file search: RuntimeError - S3 failure"
    )

    audit_service_mock.assert_called()

from unittest.mock import patch

from src.models.status_report import StatusReport, Category, ServiceObservations


@patch("src.routers.status.status_service.get_status")
def test_health(mock_status, test_client):
    so = ServiceObservations()
    a, b = so.add_checks('a', 'b')
    a.category = b.category = Category.success
    healthy_report = StatusReport(services=[so, ])
    mock_status.return_value = healthy_report

    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"Health": "OK"}


@patch("src.routers.status.status_service.get_status")
def test_health_failure(mock_status, test_client):
    so = ServiceObservations()
    so.add_check('a')  # Defaults to a failed outcome
    unhealthy_report = StatusReport(services=[so, ])
    mock_status.return_value = unhealthy_report

    response = test_client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Please try again later."}


@patch("src.routers.status.status_service.get_status")
def test_health_mixed_outcomes(mock_status, test_client):
    so = ServiceObservations()
    a, b = so.add_checks('a', 'b')  # Default to failure
    a.category = Category.success  # Single check set to success
    mixed_report = StatusReport(services=[so, ])
    mock_status.return_value = mixed_report

    response = test_client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Please try again later."}

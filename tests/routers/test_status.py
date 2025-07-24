from unittest.mock import patch

from src.models.status_report import StatusReport, Outcome, ServiceObservations


@patch("src.routers.status.status_service.get_status")
def test_status(mock_status, test_client):
    so = ServiceObservations()
    a, b = so.add_checks('a', 'b')
    a.outcome = b.outcome = Outcome.success
    healthy_report = StatusReport(services={'servicename': so})
    mock_status.return_value = healthy_report

    response = test_client.get("/status")

    assert healthy_report.is_all_success() is True
    assert response.status_code == 200
    assert response.json() == healthy_report.model_dump()


@patch("src.routers.status.status_service.get_status")
def test_status_mixed_outcomes(mock_status, test_client):
    so = ServiceObservations()
    a, b = so.add_checks('a', 'b')  # Default to failure
    a.outcome = Outcome.success  # Single check set to success
    mixed_report = StatusReport(services={'servicename': so})
    mock_status.return_value = mixed_report

    response = test_client.get("/status")

    assert mixed_report.is_all_success() is False
    assert response.status_code == 200
    assert response.json() == mixed_report.model_dump()

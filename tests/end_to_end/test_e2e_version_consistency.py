import pytest
# Using `as client`, so can easily switch between httpx and requests
import httpx as client
from tests.end_to_end.e2e_helpers import get_host_url

"""
Tests to check that requests with unversioned "plain" paths return the same results
as their /api/v1 versioned-path couterparts.
Note relevant CSV files must allow the versioned routes for these to work.
"""


HOST_URL = get_host_url()


@pytest.mark.e2e
def test_healthcheck_v1_response_consistency():
    plain_response = client.get(f"{HOST_URL}/health")
    v1_response = client.get(f"{HOST_URL}/api/v1/health")
    assert plain_response.status_code == v1_response.status_code == 200
    assert plain_response.text == v1_response.text == '{"Health":"OK"}'


@pytest.mark.e2e
def test_ping_v1_response_consistency():
    plain_response = client.get(f"{HOST_URL}/ping")
    v1_response = client.get(f"{HOST_URL}/api/v1/ping")
    assert plain_response.status_code == v1_response.status_code == 200
    assert plain_response.text == v1_response.text == '{"ping":"pong"}'

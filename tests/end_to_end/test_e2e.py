import pytest

"""
This file is for e2e tests that require an actual SDS application to run against.
They all should be decorated with custom marker @pytest.mark.e2e to enable them
to be run separately from pytest unit tests.

Manual execution:
`pipenv run pytest -m e2e` to run e2e tests only
`pipenv run pytest -m "not e2e"` to exclude e2e tests from run.
"""


@pytest.mark.e2e
def test_dummy_test():
    assert 1 == 1

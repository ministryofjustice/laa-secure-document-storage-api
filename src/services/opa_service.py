import os
from opa_client.opa import OpaClient
from opa_client.opa_async import AsyncOpaClient


OPA_HOST = os.getenv("OPA_HOST", "localhost")
OPA_PORT = os.getenv("OPA_PORT", "8181")


"""
Functions that carry out OPA evaluations.

Note:
    - OPA server needs to be running
    - OPA server needs to have the expected rego and json data files.
"""


def opa_evaluate(input_data: dict, package_path: str, rule_name: str) -> dict:
    """
    Return OPA evaluation result based on supplied input_data, package_path and rule_name.
    Note OPA server needs to have the right corresponding data for evaluations to work.
    """
    # Note alternative approach could use context manager instead of exception handling
    client = OpaClient(host=OPA_HOST, port=int(OPA_PORT))
    try:
        result = client.query_rule(input_data=input_data, package_path=package_path, rule_name=rule_name)
    except Exception as e:
        result = {"error": str(e)}
    finally:
        client.close_connection()
    return result


async def async_opa_evaluate_bad(input_data: dict, package_path: str, rule_name: str) -> dict:
    """
    First try at async version, which doesn't work. Get `'NoneType' object has no attribute 'post'`
    """
    client = AsyncOpaClient(host=OPA_HOST, port=int(OPA_PORT))
    try:
        result = await client.query_rule(input_data=input_data, package_path=package_path, rule_name=rule_name)
    except Exception as e:
        result = {"error": str(e)}
    finally:
        await client.close_connection()
    return result


async def async_opa_evaluate(input_data: dict, package_path: str, rule_name: str) -> dict:
    """
    Async version that works. Uses async context manager but loses the exception handling
    """
    async with AsyncOpaClient(host=OPA_HOST, port=int(OPA_PORT)) as client:
        result = await client.query_rule(input_data=input_data, package_path=package_path, rule_name=rule_name)
    return result

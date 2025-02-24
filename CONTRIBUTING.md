# Contributing

This document outlines the process for developing and adding functionality to the project.
See the [README.md](README.md) for instructions on setting up the project.

## Process outline

1. Branch off from `master` and name your branch after the task number and with a short title: `SDS-xx-short-title-here`.
2. Make your changes:
    * Unit tests: Add and run unit tests for your changes: `pipenv run pytest`
    * Postman tests: Make sure to get the appropriate client credentials and tokens to run the tests
    * Linting: Run flake to lint your code: `pipenv run python3 -m flake8 ./`
    * Resources: If your code uses any external resource (including environment variables), make sure to add them to appropriate pipelines and update the `README.md` file.
3. Push your branch and open a pull request.
    * Deploy to dev environment, and check status of the pipeline stages 
    * Ask the reviewers to review the pull request. 
    * Address any comments or suggestions
4. Once the pull request is merged, deploy main to the test, staging, then production environment.
5. Celebrate – Get the 'committed' trophy :)


## Making changes: Postman tests

Our GitHub workflow automation runs postman tests via a console to verify the API is working as expected. The postman
tests can also be run locally during development via the console or the Postman GUI.

When running via the console, you need to export the client id and client secret, and postman will collect the auth
token to be used during the tests. This is managed during the GitHub workflow using secrets to store the client id and
secret.

When running manually via the GUI, you will need to obtain a token for the configured test user. You can do this via
the Postman GUI or via the console using a Python script.

### Obtaining token via Postman GUI

You will need to obtain the `tenant_id`, `client_id`, and `client_secret` from the password manager. Substitute them in
whenever you see the name in curly braces, thus: `{TENANT_ID}`, `{CLIENT_ID}`, `{CLIENT_SECRET}`.

1. Open the Postman GUI
2. In the command window, enter the URL `https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token`
3. In the `Body` tab, select `x-www-form-urlencoded`
4. Add the following key-value pairs:
   a. `grant_type` = `client_credentials`
   b. `client_id` = `{CLIENT_ID}`
   c. `client_secret` = `{CLIENT_SECRET}`
   d. `scope` = `api://laa-sds-api/.default`
5. click `Send`
6. Collect the token from the response

### Obtaining token via Python script

You will need to obtain the `tenant_id`, `client_id`, and `client_secret` from the password manager. Make sure they
are available as environment variables for the script to work without changes, otherwise substitute in the values.

```python
#!/usr/bin/env python3
"""Obtain an access token using client credentials in TENANT_ID, CLIENT_ID, and CLIENT_SECRET."""
import os
import requests    

tenant_id = os.getenv('TENANT_ID')
authority = f"https://login.microsoftonline.com/{tenant_id}"
token_url = f"{authority}/oauth2/v2.0/token"

params = {
    'client_id': os.getenv('CLIENT_ID'),
    'client_secret': os.getenv('CLIENT_SECRET'),
    'scope': 'api://laa-sds-dev/.default',
    'grant_type': 'client_credentials'
}

# Request access token
response = requests.post(token_url, data=params)
if response.status_code != 200:
    print(f"Error: {response.status_code} {response.reason}")
else:
    token_response = response.json()
    print(token_response['access_token'])

```

## Making changes: Unit tests

Our tests live in the `tests` directory.
Look through the current tests to get an idea of how they are structured and how they test the parts they test.

The [PyTest docs](https://docs.pytest.org/en/stable/contents.html) are comprehensive, and you may find some additional
detail around [mocking](https://docs.python.org/3/library/unittest.mock.html) useful.

### Fixtures: Authentication, authorisation, ACLs and client configurations

We use a [fixture](https://docs.pytest.org/en/stable/fixture.html) to provide a test client with authorisation and
authentication pre-configured for a test user.
For any new routes being developed, an appropriate ACL should be added to the
`tests/fixtures/casbin_policy_allow_test_user.csv` file.

Get the test client by requesting the `test_client` as a parameter in your test function:

```python
def test_route_with_user(test_client):
    response = test_client.get("/api/v1/files/1")
    ...
```

A suitable configuration for the test client is also available as a fixture in `test_user_client_config`

```python
def test_route_with_user(test_client, test_user_client_config):
    configured_bucket = test_user_client_config.bucket
    response = test_client.get("/api/v1/bucket/")
    assert configured_bucket == response.json()["bucket"]
    ...
```

## Making changes: Linting

Linting ensures the typed code is consistent and follows best practices for ease of understanding.
We use `flake8` to lint our code in the build pipelines.
You should do this locally to check your code will pass:

```bash
$ pipenv run python3 -m flake8 ./
```

If you are using PyCharm, you can set up this up to run on command as an `External Tool`. It is also possible to set up
a `File Watcher` to run `flake8` on save, but this can be intrusive when autosave is enabled.

## Making changes: Resources

If any form of resource is required for the code to run, it should be added to the appropriate pipeline and documented
in the `README.md` file.

### Environment variables

Environment variables need to be configured in all the places where the code is run:
* Local development (pipenv, docker compose)
* Remote deployments (dev, test, production)

Add environment variables to:
* `.env` file in the root of the project
* `docker-compose.yml` file
* `.github/actions/deploy/actionsyml` file
* `.github/workflows/build-and-deploy-main.yml` file

If the variable is a secret, it should be added to the GitHub repository secrets and referenced in the appropriate
pipeline.

### AWS resources

AWS resources are managed by making changes to the `cloud-platform-environments` repository of Terraform configurations.
The SDS parts of the repo are in the
`namespaces/live.cloud-platform.service.justice.gov.uk/laa-sds-[dev|test|stg|production]` directories. After making a
change to the appropriate terraform configurations, the changes should be applied to the environment by raising a PR in
the `cloud-platform-environments` repository and notifying the Slack channel `#cloud-platform`.

## Deploying to dev environment

The authoritative source for operational topics is the
(SDS Runbook)[https://dsdmoj.atlassian.net/wiki/spaces/SDS/pages/4983652376/Runbook+Secure+Document+Storage+API]

We can do this from a pull request in GitHub: After opening a pull request, click on the `Checks` tab in the pull
request, then expand the `CI` section on the left, and click on `deploy_dev`

Outside of a pull request, we can manually trigger a run of the workflow by going to the `Actions` tab in the GitHub
repository, then selecting the `CI` workflow on the left and clicking the `Run workflow` button on the right.

## Deploying to production environment

The authoritative source for operational topics is the
(SDS Runbook)[https://dsdmoj.atlassian.net/wiki/spaces/SDS/pages/4983652376/Runbook+Secure+Document+Storage+API]

This is a multi-stage process, deploying to test, then staging, before finally to production.

### Verify 

See the sections on obtaining an access token via Postman GUI or Python script above, then use Postman to interact with
the appropriate endpoints, as listed in the (readme)[README.md].

### Rollback

To be completed...

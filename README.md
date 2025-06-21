# laa-secure-document-storage-api

A repository containing the API for the LAA shared component for secure document storage.

## Requires

Python 3.13, pipenv and docker

## Configuration

We need to configure a number of settings before the SDS API, or the local services used, will work correctly.

As a minimum you will need to configure some AWS settings, but if you want to try the SDS API locally, you will also
need some client configuration files, and some credentials if using authentication and authorisation.

### AWS configuration values

LocalStack is an AWS resource emulator which mimics the behavior of AWS in a production environment. As such, it
requires similar configuration, namely setting several environment variables.

Add the following lines to your `bash_profile` or `zshrc`:

```shell
export AWS_ACCESS_KEY_ID=dummy
export AWS_ACCESS_KEY=dummy
export AWS_SECRET_ACCESS_KEY=dummy
```

If you don't set these environment variables, LocalStack will default to the credentials defined
in `~/.aws/credentials`. Although it might seem convenient, this method requires manually updating the variables in
the `.env` file to ensure correct values when running locally.
Remember, don't include your real AWS keys in the code base or commit them to version control. When using IDE tools,
make sure your Docker-compose variables are setup correctly if you choose to use non-dummy keys.

### SDS configuration values

SDS uses tokens issued by the MoJ tenant, and there is currently no provision for entirely local authentication: All
authentication occurs with the single auth services, even when running a local SDS instance. This may be something we
change in the future.

To use any *authenticated* routes locally, you will need the `tenant_id` and `audience_id` values for the SDS API to
validate the token. Internal services teams can contact the SDS team to obtain these, and set them in your local
environment.

For each client to be authorised to use any of the SDS routes, you will also need a client configuration. See the
documentation for [generating client configs](docs/client_configurations.md). For internal services, you will need to 
follow the 
[SDS integration guide](https://dsdmoj.atlassian.net/wiki/spaces/SDS/pages/5390237878/LAA+SDS+Integration+Documentation).

For SDS developers, another team member will provide access to local development client credentials and config. They
will need to be placed in the configured directory. The default path is in a directory at the same level as the repo
directory and called `sds-client-configs`

#### Try without credentials

For users looking to try the API locally without using authentication, you can do so by creating a new config for the 
unauthenticated user `anonymous` and granting that user access to the required routes. See the docs on client configs
for more details on [generating client configs](docs/client_configurations.md).

### Running locally

To ensure a consistent development environment across different setups, we use Docker to run local instances of the
AWS services used, and the SDS API itself if needed.

You can start the full suite of applications using Docker by running the following command.
Note this is in non-daemon mode so will keep the terminal occupied, so all logs will appear as they are generated until
the process is terminated:

```shell
$ docker compose up
```

You can also start and detach the services using daemon mode:

```shell
$ docker compose up -d
...
# And now to see the logs
$ docker compose logs
...
```

This command will start the applications using the latest built image. If you want to build a new image based on the
current code, use:

```shell
$ docker compose up --build
```

You can also start just the API dependencies and run the API itself in an IDE or from the terminal.
To start the dependent services, run:

```shell
$ docker compose up -d localstack laa-clamav
```

To run the API instance from an IDE, see [IDE Setup](docs/ide_setup.md).

To run the API instance from a terminal, first install the requirements using `pipenv`, and then use that to run the
API:
```shell
$ pipenv install
...
$ pipenv run uvicorn src.main:app --reload
```

Whichever way the SDS API is launched, you can now interact with the API using: http://127.0.0.1:8000/

## Testing

### Unit testing

To run the unit tests using an IDE, follow the [IDE Setup](docs/ide_setup.md) document.

To run from the terminal, first ensure the requirements are installed:
```shell
$ pipenv install --dev
```
And then run:
```shell
$ pipenv run pytest
```

### API testing with Postman

#### Summary

We have a number of tests against this API which can run locally, in the pipeline or against any of our non-production
environments. We have pre-request scripts configured to obtain authentication tokens. A valid token is obtained before
all tests via a pre-request script on the collection. An invalid token is obtained via a pre-request script associated 
with the invalid token test.

#### Setup

- Install [Postman](https://www.postman.com/downloads/) on your Mac or other device.
  - You will require an account, create one with your `@digital.justice.gov.uk` email address
- If it doesn't exist already, create the following directory: `~/Postman` (note capital P at start)
- On Mac and other devices, Microsoft Defender may quarantine the test virus file
  - Open Micosoft Defender 
  - Open manage Virus & Threat detection settings
  - Add/Remove exclusion
  - Add folder type exclusion for this repos `/Postman` folder, and your `~/Postman` folder
  - Restore the quarantined eicar.txt file
- Copy the `eicar.txt` and `test_file.md` files from this repo's `/Postman` folder into the `~/Postman` directory.
- Start Postman and import the postman files from the `/Postman` directory via import button or menu `File > Import`.
  - include: `SecureDocStoreAPI.postman_collection.json` and all the files ending `*.postman_environment.json`
- Configure your Postman working directory location through settings > General > Working directory and set it as **~/Postman**

##### Secrets

- Contact a team member to request secrets
- We store these in a shared secure vault, you will need to add them to your local Postman vault
- Click the list icon next to the environment dropdown
- Open the vault via the red 'vault' link
- Add secrets using the naming convention from the shared vault
- Enable secret usage in tests
  - From the vault, go to settings
  - On the first page, tick enable usage in scripts
  - When you first run a request, enable secret usage in the collection

#### Running

- If testing locally, launch the API locally as described above
- Select the environment you want to test in the top right dropdown menu within the Postman UI
- "Send" the imported requests from within Postman one at a time, or right-click the collection and run the collection
- Observe the test results within Postman

## Hosting on Cloud Platform

### AWS resources
Aws resources need to be configured in cloud platform repository see below.  The resources get created on the namespace
using terraform.
When adding a resource you should export a kubernetes secret so that the secret can then be injected into the 
application as a environment variable at runtime. 

You can then use the secret directly in k8s deployment.yml

### Docker

As part of using cloud platform K8s cluster we need to create a docker image, this docker image is pushed to the ecr
repo
and from there it is eventually deployed via github actions to cloud platform.

Cloud platform run a tightly managed service on AWS, we have created 4 namespaces on cloud platform for this project

#### Namespace and endpoints

| Environment | Namespace                                                                                                                                                                 | Endpoint                                                                   |
|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| DEV         | [laa-sds-dev](https://github.com/ministryofjustice/cloud-platform-environments/tree/main/namespaces/live.cloud-platform.service.justice.gov.uk/laa-sds-dev)               | https://laa-sds-dev.apps.live.cloud-platform.service.justice.gov.uk        |
| TEST        | [laa-sds-test](https://github.com/ministryofjustice/cloud-platform-environments/tree/main/namespaces/live.cloud-platform.service.justice.gov.uk/laa-sds-test)             | https://laa-sds-test.apps.live.cloud-platform.service.justice.gov.uk       |
| STG         | [laa-sds-stg](https://github.com/ministryofjustice/cloud-platform-environments/tree/main/namespaces/live.cloud-platform.service.justice.gov.uk/laa-sds-stg)               | https://laa-sds-stg.apps.live.cloud-platform.service.justice.gov.uk        |
| PRODUCTION  | [laa-sds-production](https://github.com/ministryofjustice/cloud-platform-environments/tree/main/namespaces/live.cloud-platform.service.justice.gov.uk/laa-sds-production) | https://laa-sds-production.apps.live.cloud-platform.service.justice.gov.uk |

We have setup all the environments yet to respond on these endpoints, as it stands we will be playing around exclusively
in dev and maybe test, but the target endpoints are correct.

All infrastructure changes that need to be made have to be made in the namespace above, this includes creating
additional services like clamav and adding s3 buckets

#### Setting up local environment for cloud platform

Important cloud platform instructions

| Description                    | URL                                                                                                                   |
|--------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| Core Cloud Platform User guide | [Cloud Platform User Guide](https://user-guide.cloud-platform.service.justice.gov.uk/)                                |
| Kubectl                        | [Kubectl](https://user-guide.cloud-platform.service.justice.gov.uk/documentation/getting-started/kubectl-config.html) |

##### Optional extras with kubectl

Whilst we dont want to duplicate the guidance notes, in order to work with cloud platform namespace I find it is easier
to interact and query the cluster when we create local aliases.

I have the following alias in my setup

```
function kubesds() {
    kubectl -n "laa-sds-$1" "${@:2}"
```

I can then run some popular commands like

```
kubesds dev get ingress
kubesds dev describe ingress <ingressname>
kubesds dev get pods
kubesds dev describe pods <pod name?

```

In general the only extra this adds it saves you having to remember the namespace which is basically a requirement for
querying the cluster on every level.

### Github Actions

We have pipelines configured for linting, unit tests, postman tests, deploying to dev, then a checked deployment to
test, then staging, and finally production.

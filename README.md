# laa-secure-document-storage-api

A repository containing the API for the LAA shared component for secure document storage

## Requires

Python 3.10, pipenv and docker

## Install Requirements

### Running Docker Apps

To ensure a consistent development environment across different setups, we use Docker to run the following application(
s):

    1. DynamoDB

You can start the applications using Docker by running the following command:

    ```
    docker-compose up
    ```

This command will start the applications using the latest built image. If you want to build a new image based on the
current code, use:

    ```
    docker-compose up --build
    ```

If you prefer to work within the IDE and only want to run specific Docker services such as DynamoDB, you can specify the
service name like so:

    ```
    docker-compose up dynamodb
    ```

Service names are defined in the `docker-compose.yml` file.

#### Alpine as SDS API base image

Alpine is used because it has a smaller surface for vulnerabilities (has fewer packages), and uses fewer resources (is
smaller).

Find the list of available packages for a particular tagged image on https://hub.docker.com/_/python/tags

The differences between Alpine and a more featured image (such as `slim`) should not be relevant to the SDS service, as
interactions with the host are minimal. However, some differences of note when building are:
* `apk` instead of `apt`
* `openrc` as the init system
* `adduser` has some minor args differences

Alpine docs are:
* https://docs.alpinelinux.org/user-handbook/0.1a/index.html
* https://wiki.alpinelinux.org/wiki/Main_Page


#### Note on LocalStack

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

### Python Packages

```
pipenv install
```

## Launch

```
pipenv run uvicorn src.main:app --reload
```

You can now interact with the API using: http://127.0.0.1:8000/

## Testing

### Unit and Integration

Install additional requirements

```
pipenv install --dev
```

Run by invoking pytest

```
pipenv run pytest
```

### API with Postman

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

### Cloud Platform

### AWS resources
Aws resources need to be configured in cloud platform repository see below.  The resources get created on the namespace
using terraform.
When adding a resource you should export a kubernetes secret so that the secret can then be injected into the application as a 
environment variable at runtime. 

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
in
dev and maybe test, but the target endpoints are correct.

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

We have a basic pipeline configured to deploy to dev and test, it is early days and this will need to be further refined
to suit our working practices, this change is largely there to give a glimpse of what we can do with github
actions and the cloud platform and how to set them up.

As a bonus we are using the environments feature in github and I have temporarily put in a restriction that someone
from the sds team has to approve the deployment, we can restrict this further for higher environments or remove it
altogether.




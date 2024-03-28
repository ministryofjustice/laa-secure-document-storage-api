# laa-secure-document-storage-api
A repository containing the API for the LAA shared component for secure document storage

## Requires
Python 3.10 and pipenv

## Install Requirements
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

### API

#### Setup
- Install [Postman](https://www.postman.com/downloads/) on your Mac or other device.
- If it doesn't exist already, create the following directory: **~/Postman
- ** (note capital P at start)
- Copy the files from this repo's **tests/postman** folder into the above directory.
- Start Postman and import the `SecureDocStoreAPI.postman_collection.json`json file from the **tests/postman** directory via import button or menu `File > Import`.

#### Running
- Launch the API locally as described above
- "Send" the imported requests from within Postman
- Observe the test results within Postman

### Cloud Platform

### Docker

As part of using cloud platform K8scluster we need to create a docker image, this docker image is pushed to the ecr repo
and form there it is eventually deployed via github actions to cloud platform.

Cloud platform run a tightly managed service on AWS, we have created 4 namespaces on cloud platform for this project

#### Namespace and endpoints 

| Environment | Namespace | Endpoint |
|-------------|-----------|----------|
| DEV | [laa-sds-dev](https://github.com/ministryofjustice/cloud-platform-environments/tree/main/namespaces/live.cloud-platform.service.justice.gov.uk/laa-sds-dev) | https://laa-sds-dev.apps.live.cloud-platform.service.justice.gov.uk |
| TEST | [laa-sds-test](https://github.com/ministryofjustice/cloud-platform-environments/tree/main/namespaces/live.cloud-platform.service.justice.gov.uk/laa-sds-test) | https://laa-sds-test.apps.live.cloud-platform.service.justice.gov.uk |
| STG | [laa-sds-stg](https://github.com/ministryofjustice/cloud-platform-environments/tree/main/namespaces/live.cloud-platform.service.justice.gov.uk/laa-sds-stg) | https://laa-sds-stg.apps.live.cloud-platform.service.justice.gov.uk |
| PRODUCTION | [laa-sds-production](https://github.com/ministryofjustice/cloud-platform-environments/tree/main/namespaces/live.cloud-platform.service.justice.gov.uk/laa-sds-production) | https://laa-sds-production.apps.live.cloud-platform.service.justice.gov.uk |


We have setup all the environments yet to respond on these endpoints, as it stands we will be playing around exclusively in 
dev and maybe test. btu the target endpoints are correct.

All infrastructure changes that need to be made have to be made in the namespace above, this includes creating 
additional services like clamav and adding s3 buckets

#### Setting up local environment for cloud platform

Important cloud platform instructions

| Description                    | URL                                                                                                                   |
|--------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| Core Cloud Platform User guide | [Cloud Platform User Guide](https://user-guide.cloud-platform.service.justice.gov.uk/)                                |
| Kubectl                        | [Kubectl](https://user-guide.cloud-platform.service.justice.gov.uk/documentation/getting-started/kubectl-config.html) |

##### Optional extras with kubectl
Whilst we dont want to duplicate the guidance notes, in order to work with cloud platform namespace i find it is easier 
to interact and query the custer when we create local aliases

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

We have a basic pipeline configured to deploy to dev and test, it is early days and this will need ot be further refined
to suit our working practices, this change is largely there to give a glimpse of what we can do with github
actions and the cloud platform and how to set them up.

As a bonus we are suing environments feature in github and i have temporarily put in a restriction that someone
from the sds team has to approve the deployment, we can restrict this further for higher environments or remove it 
altogether.




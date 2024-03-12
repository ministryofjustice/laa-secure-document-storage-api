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
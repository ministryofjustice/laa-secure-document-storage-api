# laa-secure-document-storage-api
A repository containing the API for the LAA shared component for secure document storage.

## Python setup
To run this project, you need to have Python 3.9 or above and Pipenv installed on your system. a good tool to manage python versions on your macbook is [pyenv](https://github.com/pyenv/pyenv). Below are the steps to install these prerequisites:

### Install Pipenv:
Pipenv is a dependency manager for Python projects. To install it, run the following command:
    
    pip install pipenv

### Verify Pipenv Installation:
After installation, verify that Pipenv is installed correctly by checking its version:
    
    pipenv --version

### Setting Up the Project Using Pipenv
Pipenv is a highly effective tool for setting up a virtual environment and managing package dependencies in Python projects. Once you have cloned the project repository, you can establish your development environment with a few simple steps:

Initialize the Virtual Environment:
Open your terminal or command prompt and navigate to the project directory. Then, run the following command:
    
    pipenv install

This command accomplishes two key tasks:

1. Creates a Virtual Environment: If a virtual environment does not already exist for this project, pipenv install will create one. This environment is isolated from other Python environments on your system, ensuring consistency and avoiding version conflicts.

2. Installs Required Packages: It then installs all the packages listed in the Pipfile, ensuring that you have all the necessary dependencies to run the project.

### Alternative Method Using PyCharm:
If you are using PyCharm as your IDE, it can simplify this process. Simply import the project and let pycharm manage create or reuse the venv and install packages.

### Starting The Application
In order to start the application simply run
    
    uvicorn main:app

#### Alternative With Pycharm
If you are in pycharm it should have configured your ide to start the sever  by clicking on the play/debug buttons in the top right.

## Prerequisites

### LocalStack S3 setup
This project uses LocalStack via Docker compose. This will help us emulate S3 buckets on our local environments.

#### Install AWS CLI
You will need to install the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)

Localstack provides a wrapper around AWS services we can use the AWS CLI to invoke localstack instead of AWS as shown below.

#### Installing Docker
You will need to install Docker from the following link [Docker](https://docs.docker.com/engine/install/)

#### Starting Docker services
Before running the services make sure Docker is started. Then proceed to run the following command from the root of the project.
    
    docker compose up

#### Useful S3 commands with LocalStack
We have put a sample file in the root directory called ss-poc-test.txt to help verify that LocalStack has been setup correctly. Please use the following commands to verify this.

Copying a file to the bucket
    
    aws s3 cp ss-poc-test.txt s3://ss-poc-test --endpoint-url http://localhost:4566

Listing buckets
    
    aws --endpoint-url=http://localhost:4566 s3 ls

Listing objects inside buckets
    
    aws --endpoint-url=http://localhost:4566 s3 ls s3://ss-poc-test
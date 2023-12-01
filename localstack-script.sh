#!/bin/bash

awslocal s3api \
create-bucket --bucket ss-poc-test \
--region us-east-1
#!/bin/bash

awslocal s3api \
create-bucket --bucket sds-local \
--region us-east-1
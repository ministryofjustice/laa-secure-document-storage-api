# Developer: Using multipass for local development

To develop the service you need docker and postman. These may be provided via desktop install from Docker and Postman,
but there may not be available licenses for these. So this guide shows how to configure and use a development VM
instance with multipass.

## Multipass

Multipass has an application you can use to view, launch and connect to instances, but here we will use the terminal.

- Download and install [multipass](https://multipass.run/install)
- Start a new multipass instance (with 20G disk and 4G memory)
```shell
$ multipass launch --name sdsdev -d 20G -m 4G
```
- SSH into the new instance
```shell
$ multipass shell sdsdev
```

## Configure instance

Now we have the `sdsdev` instance, lets get it configured to run docker compose and postman.

- First mount the source directory so you can access it from inside the instance: `multipass mount ~/src/laa-secure-document-storage-api/ sdsdev:~/src`
- Now ssh into the instance to install everything `multipass shell sdsdev`
- Install docker, following the [install docker engine guide](https://docs.docker.com/engine/install/ubuntu/)
```shell
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add the user to the docker group
sudo usermod ubuntu -aG docker
```
- Logout (`exit`) and login again (`multipass shell sdsdev`) to get the groups to apply
- Install postman, following the [install postman cli guide](https://www.postman.com/downloads/)
```shell
curl -o- "https://dl-cli.pstmn.io/install/linux64.sh" | sh
```
- Install the `aws` from a snap [aws cli tools installation guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
```shell
sudo snap install aws-cli --classic
```
- And update the user profile to make the varying secrets available as environment variables:
```shell
echo """
export AWS_ACCESS_KEY_ID=dummy
export AWS_ACCESS_KEY=dummy
export AWS_SECRET_ACCESS_KEY=dummy
# Tenant
# This comes from laa-sds-dev in EntraID
export TENANT_ID=...

# Client - Token obtaining party
# This comes from 1Password
export CLIENT_ID=...

# Audience - Token consuming party
# Obtained from inspecting the token
export AUDIENCE_ID=...

# And you need the value of the client secret (from 1Password) for postman to get the token
export CLIENT_SECRET=...
""" >> ~/.bash_profile
# Then apply the env vars...
source ~/.bash_profile
```

## Running and testing

Assuming all of the above, you should now be able to bring up the containers
```shell
$ cd ~/src
$ docker compose build
 => [sds-api internal] load build definition from Dockerfile                                                       0.1s
 ...
 => => naming to docker.io/library/src-sds-api                                                                     0.0s
 => [sds-api] resolving provenance for metadata file
$ docker compose up -d
[+] Running 31/31
 ...  
 ✔ Container src-sds-api-1     Started                                                                             2.4s 
 ✔ Container dynamodb_local    Started
```

After bringing up a new set of containers, we currently need to run some data initialisation:

```shell
$ cd ~/src
$ ./auditdb.sh
{
    "TableNames": []
...
        "DeletionProtectionEnabled": false
    }
}
$ ./s3-bucket-create.sh
{
    "Location": "/sds-local"
...
upload: ./README.md to s3://sds-local/CRM14/README.md           
S3 bucket creation and file uploading script completed.
```

And now we can now run the postman collection of tests. For this the path is important, as some test files are used.
```shell
$ cd ~/src/Postman
$ postman collection run SecureDocStoreAPI.postman_collection.json --env-var client_id=$CLIENT_ID --env-var client_secret=$CLIENT_SECRET
No authorization data found. Please use the `postman login` command.
Refer: https://learning.postman.com/docs/postman-cli/postman-cli-options/#postman-login
...
│ total data received: 1.75kB (approx)                             │
├──────────────────────────────────────────────────────────────────┤
│ average response time: 134ms [min: 9ms, max: 636ms, s.d.: 193ms] │
└──────────────────────────────────────────────────────────────────┘
Postman api key is required for publishing run details to postman cloud.
Please specify it by using the postman login command
$ 
```

If something has gone wrong, we can check the logs for the SDS API service with `docker compose logs sds-api`

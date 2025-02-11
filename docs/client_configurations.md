# Client configuration

## Model

The client configuration links a backing storage (S3 bucket) and any storage preferences (such as file filters) to an 
authenticated client.

* `client` - Unique identifier to the requesting application.
* `service_id` - Requesting service name, may be duplicated.
* `bucket_name` - The S3 bucket name configured for the client.

`Client` This is the key by which the authenticated application is linked to the configuration. This is the OID of the 
application created in EntraID, and is available as the sub field in the token. The EntraID application must be granted
the SDS role so that the SDS API can read the auth token.

`Service ID` This is a label used in logging and audit events to link the client's actions to an LAA service or
application. Applications may use multiple clients to access the SDS API (one client per bucket), so duplicates are 
expected. The value should be the same as the production namespace from cloud platform, or the repo name of the service.

`Bucket Name` This is the S3 bucket name which the client is allowed to access. The SDS API must be given the 
appropriate IAM role to store and read files in the bucket. Buckets may be shared between clients, so duplicates are 
expected.

## Storage

The current implementation can load configurations from a datastore (DynamoDB), from JSON files, or a single-client 
local mode from environment variables. The stores used are configured via the `CONFIG_STORES` environment variable, and
will cascade in order of `db`, `file`, then `env`. Multiple stores can be specified by comma-separating the values, for
example `CONFIG_STORES=db,file`.

The current preferred store is `file`, and we manage configured clients by managing the configuration files in the
`clientconfigs` directory. We also have a helper CLI tool `configbuilder.py` for viewing and adding configs.
The files (and related ACL file) may be placed in a separate configuration repository in the future.

The ClientConfigService will return `None` if a config is not found, so we also have a helper method
`client_config_service.get_config_for_client_or_error` which will raise a `403` exception if a config is not found. 
The result (a `ClientConfig` or `None`) is cached by the service for a configurable time, defaulting to 300 seconds
(5 minutes). Use `CONFIG_TTL` to specify a time-to-live in seconds.

### `file` store

The file store loads JSON format files from `CONFIG_DIR` (defaults to `/app/clientconfigs/`). Files are named with the
`client` value (so `abc-123-def.json`), and may be organised in directories below the configured root.

For ease of use, we have a helper CLI tool `configbuilder.py` which can be used to view and add client configurations.

To list all client configurations, run
```shell
$ ./configbuilder.py list
```

To view the current configuration for a specific client, run
```shell   
$ ./configbuilder.py get {client}
```

If you have a value (such as a service or bucket name), you can find all clients which contain that value in their
configuration by running
```shell
$ ./configbuilder.py find {value}
```

To add a new client interactively, run
```shell
$ ./configbuilder.py add
```

To add a new client configuration where you already know the values, run
```shell
$ ./configbuilder.py add --client {client} --bucket_name {bucket} --service_id {service}
```

### `db` store

The `db` store is a DynamoDB table specified via the environment variable `CONFIG_TABLE` and a local instance can be 
initialised and have a config inserted using the `configdb.sh` script.

To initialise a table, run 
```shell
$ ./configdb.sh init
```
and to add a client config run
```shell
$ ./configdb.sh client {client} {bucket} {service}
```
When adding a client config, if values are not provided the script will prompt:
```shell
$ ./configdb.sh client
Enter client id: abc-def-ghi
Enter bucket name: local-test-bucket
Enter service id (default: abc-def-ghi): 

Client : abc-def-ghi
Service: 
Bucket : local-test-bucket

Adding client config to LOCAL_CONFIG_TABLENAME --region=eu-west-2 --endpoint-url http://localhost:8100
Continue? (y/n) y
$ 
```

### `env` store

The env store must only be used for local development, and must be configured as a second store, not the exclusive 
store. It supports a single client specified using all of the following environment variables:
* `LOCAL_CONFIG_CLIENT`
* `LOCAL_CONFIG_BUCKET_NAME`
* `LOCAL_CONFIG_SERVICE_ID` 

## Use cases

### New production client

We have an external team who want to use SDS for their document storage needs, and we want to allow that access both in
terms of configuration and ACL.

1. The requesting service needs:

   * An EntraID application

     * The application must have been granted the SDS role so that the auth token can be read by the SDS API

     * The OID of the application must be provided

   * An S3 bucket which will be the backing store for SDS API access

     * The bucket is added by creating a name in the SDS CP namespace, as documented elsewhere

     * The bucket name must be provided when adding a config

   * The name of the service

     * This should be the same as the owning application's production namespace in Cloud Platforms, or the repository
       name

   * Which routes the client should have access to:

     * GET /retrieve_file

     * POST /save_file

2. Use the `configbuilder.py` CLI helper to add a client config.

    Example content in file `clientconfigs/000-000-000.json`: 
    ```bash
   $ ./configbuilder.py add
    ```


3. Update the ACL policy file (`authz/casbin_policy_prod.csv`) to allow the new client to access the routes they need. 

    Sample fragment of ACL allowing client `000-000-000` to save and retrieve from the bucket named `abc-def-hij`: 
    ```csv
    p, 000-000-000, /retrieve_file, GET
    p, 000-000-000, /save_file, POST
    p, 000-000-000, abc-def-hij, (READ)|(CREATE)
    ```


### New local development client

As a developer of either a requesting service or of the SDS API itself, I need a user to access the service and to 
specify which locally available buckets should be used.

1. The developer needs an EntraID application with the SDS role. The SDS API currently only allows applications
   authenticated via EntraID, so a dev or test application needs to be created in EntraID before the API is usable
   locally.

2. Use the `configbuilder.py` CLI helper to add a config
 
    ```bash
    $ ./configbuilder.py add
    ```

3. Update the ACL policy to allow the new client to access the routes they need. For purely local development, you can
   use the special username authenticated to the ACL found in the authz directory.

    Sample fragment of ACL allowing client `000-000-000` to save and retrieve from `local-test-bucket`: 
    ```csv
    p, 000-000-000, /retrieve_file, GET
    p, 000-000-000, /save_file, POST
    p, 000-000-000, local-test-bucket, (READ)|(CREATE)
    ```

### Remove production client

As a maintainer of the SDS API service, I want to remove an application that no longer has access to the service.

1. Find the application config file named after the application_oid in `clientconfigs` and remove it.

2. Commit and push the change.

3. To ensure any cached copies are removed, ensure the appropriate sds-api container is restarted.

As an improvement, the configurations should be held in a repository and a push into the repo would trigger a restart
of the SDS API container.

### Automated test client

As a developer of the SDS API, I want to run automated tests with a local test application, but I do not want to store 
the config.

1. Ensure the authorisation backend has been mocked to authenticate your test application

2. Update the environment (likely the .env file) with the following values:
```shell
CONFIG_SOURCES=file,env
LOCAL_CONFIG_CLIENT={your-client-name}
LOCAL_CLIENT_BUCKET={your-localstack-bucket-name}
LOCAL_CLIENT_SERVICE_ID={any-string-label-for-local-test}
```

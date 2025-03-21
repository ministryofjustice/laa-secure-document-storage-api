# Client configuration

## Model

The client configuration links a backing storage (S3 bucket) and any storage preferences (such as file validators) to an 
authenticated client.

* `azure_client_id` - Unique identifier to the requesting application, the `username` of the client.
* `azure_display_name` - Human readable label for the requesting client, may be duplicated.
* `bucket_name` - The S3 bucket name configured for the client.
* `file_validators` - A list of file validators to apply to files saved by the client.

`Azure Client ID` This is the key by which the authenticated application is linked to the configuration.
This is the ID labelled `Application (client) ID` in the Azure portal, and is available as the `azp` field in the auth 
token. The app registration must have the `LAA_SDS_ALL` API permission assigned.

`Azure Display Name` This is a label used in logging and audit events to link the client's actions to an LAA service or
application, and for easier management of clients. The field is labelled `Display Name` in the Azure portal.
A requesting service may use multiple Azure app registrations to access the SDS API (one client per bucket), so
duplicates are expected.

`Bucket Name` This is the S3 bucket name which the client is allowed to access, and is added to the SDS Cloud Platform
namespace, as specified in the SDS integration documentation.
Buckets may be shared between clients, so duplicates are expected.

`File Validators` This is a list of file validators to apply to files saved by the client. The file is only saved if 
all validators pass. The validators are specified as a list of objects, which contain the name of the validator and any
arguments required by the validator.

For convenience, we organise the client configurations into directories based on the requesting service (such as
`laa-sds`), then the `azure_display_name` value, and finally the files are named with the `azure_client_id` value.

## Storage

The current implementation can load configurations from from JSON files or a single-client local mode from environment
variables. The stores used are configured via the `CONFIG_STORES` environment variable, and will cascade in order of
`file`, then `env`. Multiple stores can be specified by comma-separating the values, for example
`CONFIG_STORES=file,env`.

We manage configured clients by managing the configuration files in the `clientconfigs` directory. 
We also have a helper CLI tool `configbuilder.py` for viewing and adding configs.
The files (and related ACL file) may be placed in a separate configuration repository in the future.

The ClientConfigService will return `None` if a config is not found, so we also have a helper method
`client_config_service.get_config_for_client_or_error` which will raise a `403` exception if a config is not found. 
The result (a `ClientConfig` or `None`) is cached by the service for a configurable time, defaulting to 300 seconds
(5 minutes). Use `CONFIG_TTL` to specify a time-to-live in seconds.

### `file` store

The file store loads JSON format files from `CONFIG_DIR` (defaults to `/app/clientconfigs/`).
Files are organised into directories based on the requesting parent service (such as `laa-sds`), then the
`azure_display_name` value, and finally the files are named with the `azure_client_id` value (so `abc-123-def.json`).

For ease of use, we have a helper CLI tool `configbuilder.py` which can be used to view and add client configurations.

To list all client configurations, run:
```shell
$ ./configbuilder.py list
```

To view the current configuration for a specific client, get the Azure application (client) ID (or the start of the ID)
and run:
```shell   
$ ./configbuilder.py get {client-id}
```

If you have a value (such as a service name or bucket name), you can find all clients which contain that value in their
configuration by running:
```shell
$ ./configbuilder.py find {value}
```

To add a new client interactively, run:
```shell
$ ./configbuilder.py add
```

To add a new client configuration where you already know the values, run:
```shell
$ ./configbuilder.py add --azure-client-id {client} \
  --bucket-name {bucket} \
  --azure-display-name {service} \
  --service-name {service_name}
```
This will add a new client configuration with the recommended file validators for the service.

The config files are plain JSON and can be edited in any text editor. The structure is as follows:
```json
{
  "azure_client_id": "000-000-000",
  "azure_display_name": "Service Name",
  "bucket_name": "bucket-name",
  "service_name": "service-name",
  "file_validators": [
    {
      "name": "file_validator_name",
      "validator_kwargs": {
        "arg1": "value1",
        "arg2": "value2"
      }
    }
  ]
}
```
However, we also provide an interactive editor in the configbuilder tool which can be used to reset routes and file
validators. To interactively edit a client configuration, run:
```shell
$ ./configbuilder.py edit {client-id}
```



### `env` store

The env store must only be used for local development, and must be configured as a second store, not the exclusive 
store. It supports a single client specified using all of the following environment variables:
* `LOCAL_CONFIG_AZURE_CLIENT_ID`
* `LOCAL_CONFIG_BUCKET_NAME`
* `LOCAL_CONFIG_AZURE_DISPLAY_NAME` 

## Use cases

### New production client

We have an external team who want to use SDS for their document storage needs, and we want to allow that access both in
terms of configuration and ACL.

1. The requesting service needs:

   * An EntraID app registration

     * The app registration must have the `LAA_SDS.ALL` API permission assigned
     * The `Application (client) ID` must be provided
     * The `Display Name` must be provided
     * The repo or Cloud Platform name of the requesting service should be provided

   * An S3 bucket which will be the backing store for SDS API access

     * The bucket is added by creating a name in the SDS CP namespace, as documented elsewhere

     * The bucket name must be provided when adding a config

   * Which routes the client should have access to:

     * GET /retrieve_file

     * POST /save_file

2. Use the `configbuilder.py` CLI helper to add a client config.
 
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

1. The developer needs an EntraID app registration with the `LAA_SDS_ALL` API permission.
   The SDS API currently only allows applications authenticated via EntraID, so a dev or test application needs to be
   created in EntraID before the API is usable locally.

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

1. Find the application config file named after the Azure application (client) ID in `clientconfigs` and remove it.

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
LOCAL_CONFIG_AZURE_CLIENT_ID={your-client-name}
LOCAL_CLIENT_BUCKET={your-localstack-bucket-name}
LOCAL_CLIENT_AZURE_DISPLAY_NAME={any-string-label-for-local-test}
```

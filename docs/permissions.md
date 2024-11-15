# Permissions (Authorisation)

Permissions are what a user can do once that user has verified their identity (authenticated).

This service uses the external EntraID for authentication, and an internal casbin package for authorisation.

From a requesting service perspective, you need:
- A client id and associated token from EntraID (authentication)
- A storage unit (currently an S3 bucket)
- A configuration enabling or disabling the features required by your service (which sets some authorisation)

Separate documents cover these three parts from a requesting service perspective.
This document covers authorisation from an internal implementors perspective.

## Casbin

Casbin starts with a model telling it how to apply rules, and a policy which is a data file containing the authorisation
rules. An enforcer is created using the model and policy files, and this provides a simple interface to check a subject
(the user) can perform an action (such as update or get) on an object (such as a bucket or an endpoint).

## Control access to endpoints

We use `fastapi-authz` as middleware which enforces authz for each request. The middleware requires authentication to be
implemented as a subclass of `AuthenticationBackend` which ensures a type of `BaseUser` and a list of scopes (OAuth for
permission names) is returned. The implementation of token-based authentication is covered in a separate document.

The enforcer and middleware are configured at the app level (in `main.py`):
```python
import casbin, os, fastapi, fastapi_authz, starlette
# Import our token auth backend
from src.middleware.auth import BearerTokenAuthBackend
# Using a SyncedEnforcer to get periodic reloading of policy file
enforcer = casbin.SyncedEnforcer(
    model=os.environ.get('CASBIN_MODEL', '/authz/model.conf'),
    adapter=os.environ.get('CASBIN_POLICY', '/authz/policy.csv'),
)
app = fastapi.FastAPI()
# Order matters here: Casbin middleware first, then the auth backend
# Call the casbin middleware for each request...
app.add_middleware(
    fastapi_authz.CasbinMiddleware,
    enforcer=enforcer
)
# ...and call an authentication backend to get the user.
app.add_middleware(
    starlette.middleware.authentication.AuthenticationMiddleware,
    backend=BearerTokenAuthBackend()
)
```

Then all we need are policy rules for accessing endpoints:

```csv
# policy.csv

# Control a specific rest action on an endpoint
p, client-username, /retrieve_file, GET
p, client-username, /save_file, POST

# Allow all rest actions on an endpoint
p, client-username, /controller, *

# Allow two different rest actions on an endpoint
p, client-username, /controller, (GET)|(POST)

# Allow anonymous access to an endpoint
p, anonymous, /health, GET
```


## Control access to data objects

We can check for permissions separately to the URL, we just need an enforcer with the same model and policy.

```python
import casbin, os
# Requires the user from the middleware
user = 'client-username'
enforcer = casbin.Enforcer(
    model=os.environ.get('CASBIN_MODEL', '/authz/model.conf'),
    adapter=os.environ.get('CASBIN_POLICY', '/authz/policy.csv'),
)
enforcer.enforce(user, 'data-object', 'read')
```

And the policy rule that grants access:
```
p, client-username, data-object, read
```

Note that if you are checking an action which is mapped to an enum, you may need to use the value or name of the enum
because the default `__str__` value includes the enum class.
```python
import enum
class Operation(enum.Enum):
    CREATE = 'CREATE'
    READ = 'READ'

# Policy action would be 'Operation.READ'
enforcer.enforce(user, 'data-object', Operation.READ)
# Policy action would be 'READ'
enforcer.enforce(user, 'data-object', Operation.READ.value)
```

### Using dependency injection to get the requesting user

Assuming the casbin middleware and auth backend are in place (see above), we can use dependency injection to provide the requesting user to the endpoint method:

```python
# dependencies.py
import fastapi, starlette, casbin, os
def request_user_dep(request: fastapi.requests.Request) -> starlette.authentication.BasicUser:
    return request.user

# routers/endpoint.py
router = fastapi.APIRouter()
@router.get('/retrieve_file')
async def retrieve_file(client_user = fastapi.params.Depends(request_user_dep), file:str = fastapi.params.Query(None, min_length=1)):
    enforcer = casbin.Enforcer(
        model=os.environ.get('CASBIN_MODEL', '/authz/model.conf'),
        adapter=os.environ.get('CASBIN_POLICY', '/authz/policy.csv'),
    )
    enforcer.enforce(client_user.username, 'data-object', 'read')
    # ...
```

## Developing and checking models and policies

Casbin has an [editor](https://casbin.org/editor/) which can be used to check the policy rules and the model.

Logging can be quite detailed, and is controlled by setting the `LOGGING_LEVEL_CASBIN` environment variable. If not set,
casbin will not emit any logs.


from src.services.authz_service import AuthzServiceSingleton

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

*Important* The model controls how the policy rules are interpreted, and by default matches are straight string
comparisons which means strings we may expect to work (such as '*' meaning 'any value') will not actually work without
also changing the model.

## Control access to endpoints

We use `fastapi-authz` as middleware which enforces authz for each request. The middleware requires authentication to be
implemented as a subclass of `AuthenticationBackend` which ensures a type of `BaseUser` and a list of scopes (OAuth for
permission names) is returned. The implementation of token-based authentication is covered in a separate document.

A simple generic implementation is:

```python
# Simplified example main.py
import casbin, fastapi, fastapi_authz, starlette
from yourapp.middleware.auth import ProjectSpecificAuthentication
enforcer = casbin.Enforcer(model='/path/to/model.conf', adapter='/path/to/policy.csv')
app = fastapi.FastAPI()
# Order matters here: Casbin middleware first, then the auth backend
app.add_middleware(fastapi_authz.CasbinMiddleware, enforcer=enforcer)
app.add_middleware(starlette.middleware.authentication.AuthenticationMiddleware, backend=ProjectSpecificAuthentication())
# ...
```

For the SDS implementation, we want to use the enforcer to check for permissions to do actions once inside the endpoint:
Actions such as checking if a client can scan a file, or if a particular file filter should be applied. To support this,
we make a single enforcer available as a service. So the SDS implementation looks more like:

```python
# main.py
...
app = fastapi.FastAPI()
# Order matters here: Casbin middleware first, then the auth backend
app.add_middleware(fastapi_authz.CasbinMiddleware, enforcer=AuthzService().enforcer)
app.add_middleware(starlette.middleware.authentication.AuthenticationMiddleware, backend=BearerTokenAuthBackend())


# ...
# Inside a route...
@router.get('/example')
async def get_example(request: Request, file: str = fastapi.params.Query(None, min_length=1)):
    # If a request gets here, it has already been authenticated and authorised for this endpoint
    # but we may want to check additional permissions...
    
    # Optional permission: Only if the user has this permission:
    if authz_service.enforce(request.user.username, file, 'action-name'):
        # User can perform 'action-name' on the file
        ...
    
    # Or a required permission: Raise an exception if the user does not have this permission:
    authz_service.enforce_or_error(request.user.username, file, 'action-name')
    # ...
```

Then all we need are policy rules for accessing endpoints. Here are some generic examples:

```csv
# policy.csv

# Control a specific rest action on an endpoint
p, client-username, /retrieve_file, GET
p, client-username, /save_file, POST

# Allow unauthenticated access to an endpoint
# This works because the middleware sets unauthenticated user object usernames to 'anonymous', so no model changes
# are needed to support this.
p, anonymous, /health, GET
```

To support specifying multiple actions on an endpoint, we need to ensure the model supports this.
For example, to allow both GET and POST on an endpoint:

```csv
# policy.csv
p, client-username, /controller, (GET)|(POST)

# model.conf
...
[matchers]
# Replace the default r.act == p.act with a regex match:
m = ... && regexMatch(r.act, p.act)
```


## Control access to data objects

We can check for permissions separately to the URL, we just need an enforcer with the same model and policy.

For efficiency in the SDS implementation, we use the same enforcer as the middleware acting on the endpoints, and this
is achieved using a singleton service:

```python
# ...
from src.services import authz_service

# An optional action using the passthrough to the enforcer:
if authz_service.enforce(request.user.username, data_object_id, 'ACTION'):
    # User has permission
    ...

# Or a required action, raise a 403 error if the user does not have permission:
authz_service.enforce_or_error(request.user.username, data_object_id, 'ACTION')
# ...
```

Note that if you are checking an action which is mapped to an enum, you may need to use the value or name of the enum
because the default `__str__` value includes the enum class.
```python
# Simplified example
import enum
class Operation(enum.Enum):
    CREATE = 'CREATE'
    READ = 'READ'

# The matching policy action would be 'Operation.READ'
if enforcer.enforce(user, 'data-object', Operation.READ):
    ...
# The matching policy action would be 'READ'
if enforcer.enforce(user, 'data-object', Operation.READ.value):
    ...
```

### Using regex, or wildcards, on data object matching

An example of using regex for data objects could be to apply a rule to all files of a specific type.
To support this, we need to update the model to allow regex matching, but we do need to be careful to not accidentally
allow operations on endpoints.

```
# model.conf
...
m = r.sub == p.sub && regexMatch(r.obj, p.obj) && regexMatch(r.act, p.act) 
```
    
Then we can set policies thus:
```
# policy.conf
...
# Allow test_user to read any file that does not start with a leading '/'
p, test_user, [^/].*, READ
# But other_user can only read pdf files
p, other_user, .*pdf, READ
```

And check permissions thus:

```python
# route.py
...
if authz_service.enforce(request.user.username, file, OperationType.READ.value):
    # User has permission
    ...

```


### Using dependency injection to get the requesting user

Assuming the casbin middleware and auth backend are in place (see above), we can use dependency injection to provide the requesting user to the endpoint method:

```python
# dependencies.py
import fastapi, starlette


def request_user_dep(request: fastapi.requests.Request) -> starlette.authentication.BasicUser:
    return request.user


# routers/endpoint.py
from src.services import authz_service

router = fastapi.APIRouter()


@router.get('/retrieve_file')
async def retrieve_file(
        client_user=fastapi.Depends(request_user_dep),
        file: str = fastapi.Query(None, min_length=1)
    ):
    if authz_service.enforce(client_user.username, file, 'action-name'):
        # User has permission
        ...
    # ...
```

## Developing and checking models and policies

Casbin has an [editor](https://casbin.org/editor/) which can be used to check the policy rules and the model.

Logging can be quite detailed, and is controlled by setting the `LOGGING_LEVEL_CASBIN` environment variable in SDS.
If not set, casbin will not emit any logs.

Remember the policy rules do not support special strings or combinations without support from the model.

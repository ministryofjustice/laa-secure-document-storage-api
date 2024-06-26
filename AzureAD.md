# Azure AD/Entra ID Process

## Introduction

As part of the SDS authentication/authorization process, we aim to ensure that client applications calling SDS have the correct privileges. Optionally, we can associate their permissions with a bucket where files are stored.

## Azure AD/Entra ID Overview

Azure Active Directory (Azure AD) facilitates interservice authentication/authorization by providing identity services that applications use for authentication and authorization. This allows users to sign in and access resources.

For interservice communication:

- **Client Application (EDM)**: Authenticates with Azure AD and requests an access token for the resource service.
- **Resource Service (SDS)**: The client service uses the token to authenticate its requests. The resource service validates the token by examining its digital signatures and claims.

These actions rely on developer-defined permissions and consent grants in Azure AD to govern access from client applications to specific resource services.

## Application Registration

We will register two applications: a client and a server. In practice, you will be either a client or a server and will pick one or the other.

### Register the Service App (LAA-SDS-LOCAL)

1. Navigate to the [App registrations page](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade) on the Microsoft Identity platform for developers.
2. Select **New registration**.
3. On the **Register an application** page:
    - Enter a meaningful application name, e.g., `laa-sds-local`.
    - Leave **Supported account types** on the default setting: "Accounts in this organizational directory only."
4. Select **Register** to create the application.
5. On the app **Overview** page, record the **Application (client) ID** for later configuration in Visual Studio.
6. Select the **Expose an API** section:
    - Use the **Set** button to generate the default AppID URI in the form `api://laa-sds-local`. Format: `api://<your-custom-uri>`.
    - Click **Save**.
7. Go to **App Roles**:
    - Create an app role:
        - **Display name**: `Laa_SDS_Local_Role`
        - **Application**: Checked
        - **Value**: Will be sent in the roles for the token
        - **Description**: Provide a useful description
        - **Enable this app role**
        - Click **Apply**
    - Click on **Manifest** and verify the role exists inside `appRoles`.

### Register the Client App (EDM)

1. Navigate to the [App registrations page](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade) on the Microsoft Identity platform for developers.
2. Select **New registration**.
    - Enter a meaningful application name, e.g., `edm`.
    - In the **Supported account types** section, select "Accounts in this organizational directory only ({tenant name})."
3. Select **Register** to create the application.
4. On the app **Overview** page, record the **Application (client) ID** for later configuration in Visual Studio.
5. Go to the **Certificates & secrets** page, in the **Client secrets** section:
    - Choose **New client secret**:
        - Type a key description (e.g., `app secret`).
        - Select a key duration (e.g., 1 year, 2 years).
        - Click **Add** and copy the key value. Save it in a secure location; it will not be displayed again.
6. On the app's pages, select **API permissions**:
    - Click the **Add a permission** button.
    - Ensure the **My APIs** tab is selected.
    - Select the API created earlier, e.g., `laa-sds-local`.
    - In the **Application permissions** section, check `Laa_SDS_Local_Role`.
    - Click **Add permissions**.
7. You need to be a Microsoft Entra tenant admin to grant consent:
    - Click **Grant/revoke admin consent for {tenant}** and confirm to grant permissions for all accounts in the tenant.

## Using Tokens in Python

### How to Get a Token

```python
class AzureAuthenticator():
    def __init__(self, client_id, client_secret, authority, scope, app=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.authority = authority
        self.scope = scope
        self.app = app or msal.ConfidentialClientApplication(client_id=self.client_id, authority=self.authority,
                                                             client_credential=self.client_secret)

    def acquire_token(self):
        result = self.app.acquire_token_for_client(self.scope)
        if "access_token" in result:
            return result["access_token"]
        else:
            return None
        
    #--------------------------------------------

    auth = AzureAuthenticator(client_id, client_secret, authority, [sds_scope])
    token = auth.acquire_token()
```



### How to Verify a Token

```python
    import requests
    from jose import jwt, jwk
    from cachetools import cached, TTLCache
    from typing import Tuple
    
    @cached(TTLCache(maxsize=100, ttl=3600))
    def fetch_oidc_config(tenant_id):
        url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
        return requests.get(url).json()
    
    @cached(TTLCache(maxsize=100, ttl=3600))
    def fetch_jwks(jwks_uri):
        return requests.get(jwks_uri).json()
    
    def validate_token(token: str, aud: str, tenant_id: str) -> Tuple[bool, dict]:
        oidc_config = fetch_oidc_config(tenant_id)
        jwks_uri = oidc_config['jwks_uri']
        jwks = fetch_jwks(jwks_uri)
        unverified_header = jwt.get_unverified_header(token)
        rsa_key_data = None

    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa_key_data = key
            break

    is_valid = False
    payload = {}

    if rsa_key_data:
        try:
            rsa_key = jwk.construct(rsa_key_data, 'RS256')
            payload = jwt.decode(
                token,
                rsa_key.to_dict(),
                algorithms=['RS256'],
                audience=aud,
                issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0"
            )
            is_valid = True
        except Exception as error:
            print(f'The token is invalid: {error}')

    return is_valid, payload
    
    #--------------------------------------------
    
    is_valid, payload = validate_token(token, audience, tenant_id)
    
    if is_valid:
        print('The token is valid', payload)
    else:
        print('The token is invalid')
```
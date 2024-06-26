from azureadclient.azure_authenticator import AzureAuthenticator
from validation.token_validator import validate_token


def test_acquire_token():

    tenant_id = os.environ.get('TENANT_ID')
    audience = os.environ.get('AUDIENCE')

    client_id = os.environ.get('CLIENT_ID')
    client_secret = os.environ.get('CLIENT_SECRET')
    sds_scope = os.environ.get('SDS_SCOPE')

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    auth = AzureAuthenticator(client_id, client_secret, authority,
                              [sds_scope])


    token = auth.acquire_token()
    # ----------- End  Client side can get the token like this--------------------


    #------  Start Server side  will do this with token after receving via header -------------------




    is_valid, payload = validate_token(token, audience, tenant_id)

    if is_valid:
        print('The token is valid', payload)
    else:
        print('The token is invalid')

    # ------  End Server side  will do this with token after receving via header -------------------

    # assert
    assert token is not None, "token retrieval failed"

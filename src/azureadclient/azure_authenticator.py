import msal


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

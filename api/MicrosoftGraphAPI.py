import requests
from system.Config import Config

class MicrosoftGraphAPI:
    graph_scope_url = 'https://graph.microsoft.com/.default'
    securitycenter_scope_url = 'https://api.securitycenter.microsoft.com/.default'

    @staticmethod
    def get_security_center_access_token():
        return MicrosoftGraphAPI.__get_access_token(scope=MicrosoftGraphAPI.securitycenter_scope_url)

    @staticmethod
    def get_graph_access_token():
        return MicrosoftGraphAPI.__get_access_token(scope=MicrosoftGraphAPI.graph_scope_url)

    def __get_access_token(scope: str):
        response = requests.post(
            url=f"https://login.microsoftonline.com/{Config.tenant_id}/oauth2/v2.0/token",
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            data={
                'client_id': Config.client_id,
                'scope': scope,
                'client_secret': Config.client_secret,
                'grant_type': 'client_credentials',
            }
        )

        if 200 <= response.status_code < 300:
            print(f"[✓] Successfully obtained access token for scope: {scope}")
            return response.json()['access_token']
        else:
            raise ValueError(f"Error {response.status_code}: {response.text}")
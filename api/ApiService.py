from system.Config import Config
import requests

class ApiService:
    # Quick access variables -------------------------------------------------------------------------------------------
    __azure_access_token = None

    # Microsoft Graph Endpoints ----------------------------------------------------------------------------------------
    @staticmethod
    def get_devices_from_page(page_url):
        response = requests.get(
            url=page_url,
            headers={
                'Authorization': f'Bearer {ApiService.__azure_access_token}',
                'Content-Type': 'application/json'
            },
        )
        if 200 <= response.status_code < 300:
            return response.json().get('value'), response.json().get('@odata.nextLink')
        else:
            raise ValueError(f"Error {response.status_code}: {response.text}")

    # Access tokens methods --------------------------------------------------------------------------------------------
    @staticmethod
    def get_azure_access_token():
        ApiService.__azure_access_token = (ApiService.
                                __get_microsoft_online_access_token(scope='https://graph.microsoft.com/.default'))

    # @staticmethod
    # def get_microsoft_defender_access_token():
    #     ApiService.__microsoft_defender_access_token = ApiService.__get_microsoft_online_access_token(
    #         scope='https://api.securitycenter.microsoft.com/.default')

    @staticmethod
    def __get_microsoft_online_access_token(scope: str):
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
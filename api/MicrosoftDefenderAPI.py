from api.MicrosoftGraphAPI import MicrosoftGraphAPI
import requests

class MicrosoftDefenderAPI:
    # Quick access variables -------------------------------------------------------------------------------------------
    __access_token = None

    # Microsoft Graph Endpoints ----------------------------------------------------------------------------------------
    @staticmethod
    def get_devices():
        response = requests.get(
            url=f"https://api.security.microsoft.com/api/machines",
            headers={
                'Authorization': f'Bearer {MicrosoftDefenderAPI.__access_token}',
                'Content-Type': 'application/json'
            },
        )

        if 200 <= response.status_code < 300:
            return response.json().get('value')
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            raise ValueError(error_message)

    # Access tokens methods --------------------------------------------------------------------------------------------

    @staticmethod
    def get_access_token():
        MicrosoftDefenderAPI.__access_token = MicrosoftGraphAPI.get_access_token(
            scope='https://api.securitycenter.microsoft.com/.default')


from api.MicrosoftGraphAPI import MicrosoftGraphAPI
import requests

class IntuneAPI:
    # Quick access variables -------------------------------------------------------------------------------------------
    __access_token = None

    # Microsoft Graph Endpoints ----------------------------------------------------------------------------------------
    @staticmethod
    def get_devices_from_page(page_url):
        response = requests.get(
            url=page_url,
            headers={
                'Authorization': f'Bearer {IntuneAPI.__access_token}',
                'Content-Type': 'application/json'
            },
        )
        if 200 <= response.status_code < 300:
            return response.json().get('value'), response.json().get('@odata.nextLink')
        else:
            raise ValueError(f"Error {response.status_code}: {response.text}")

    # Access token -----------------------------------------------------------------------------------------------------
    @staticmethod
    def get_access_token():
        IntuneAPI.__access_token = MicrosoftGraphAPI.get_graph_access_token()
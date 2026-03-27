from api.MicrosoftGraphAPI import MicrosoftGraphAPI
import requests

class IntuneAPI:
    # Quick access variables -------------------------------------------------------------------------------------------
    __access_token = None

    # Microsoft Graph Endpoints ----------------------------------------------------------------------------------------
    @staticmethod
    def get_devices_from_page(page_url):
        return MicrosoftGraphAPI.get_devices_from_page(page_url, IntuneAPI.__access_token)

    # Access token -----------------------------------------------------------------------------------------------------
    @staticmethod
    def get_access_token():
        IntuneAPI.__access_token = MicrosoftGraphAPI.get_graph_access_token()
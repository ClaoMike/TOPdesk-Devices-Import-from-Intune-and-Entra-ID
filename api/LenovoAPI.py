from system.Config import Config
import requests

class LenovoAPI:
    @staticmethod
    def get_lenovo_warranties(params: str):
        url = f"https://supportapi.lenovo.com/v2.5/warranty?{params}"
        headers = {
            "ClientID": Config.lenovo_client_id,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = requests.post(url, headers=headers)

        if 200 <= response.status_code < 300:
            return response.json()
        else:
            raise ValueError(f"Error {response.status_code}: {response.text}")
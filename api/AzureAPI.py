from api.MicrosoftGraphAPI import MicrosoftGraphAPI
import requests

class AzureAPI:
    # Quick access variables -------------------------------------------------------------------------------------------
    __access_token = None

    # Microsoft Graph Endpoints ----------------------------------------------------------------------------------------
    @staticmethod
    def get_devices_from_page(page_url):
        return MicrosoftGraphAPI.get_devices_from_page(page_url, AzureAPI.__access_token)

    @staticmethod
    def batch_get_registered_users(device_ids):
        url = "https://graph.microsoft.com/v1.0/$batch"
        headers = {
            "Authorization": f"Bearer {AzureAPI.__access_token}",
            "Content-Type": "application/json"
        }

        requests_payload = [
            {
                "id": device_id,
                "method": "GET",
                "url": f"/devices/{device_id}/registeredUsers"
            }
            for device_id in device_ids
        ]

        all_results = {}
        for i in range(0, len(requests_payload), 20):
            chunk = requests_payload[i:i + 20]
            response = requests.post(url, headers=headers, json={"requests": chunk})
            data = response.json()

            for item in data.get("responses", []):
                dev_id = item.get("id")
                if item["status"] == 200:
                    users = item["body"].get("value", [])
                    user_id = users[0].get("id") if users else None
                    all_results[dev_id] = user_id
                else:
                    all_results[dev_id] = None
        return all_results

    # Access token -----------------------------------------------------------------------------------------------------
    @staticmethod
    def get_access_token():
        AzureAPI.__access_token = MicrosoftGraphAPI.get_graph_access_token()
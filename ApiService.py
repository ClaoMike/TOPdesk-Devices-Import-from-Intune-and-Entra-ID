from Config import Config
import requests
from IntuneDevice import IntuneDevice

class ApiService:
    # Quick access variables -------------------------------------------------------------------------------------------
    __azure_access_token = None
    # __microsoft_defender_access_token = None

    # TOPdesk Endpoints ------------------------------------------------------------------------------------------------
    @staticmethod
    def archive_asset(asset_id: str):
        response = requests.post(
            url=        f"https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets/{asset_id}/archive",
            auth=       (Config.topdesk_username, Config.topdesk_password),
            headers=    {'Content-Type': 'application/json'},
            json=       {"reasonId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}
        )

        if 200 <= response.status_code < 300:
            print(response.json())
            return
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            raise ValueError(error_message)

    @staticmethod
    def delete_assets(assets):
        if len(assets) != 0:
            print(f"Deleting {len(assets)} assets")

            response = requests.post(
                url=f"https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets/delete",
                auth=(Config.topdesk_username, Config.topdesk_password),
                headers={
                    'Content-Type': 'application/json'
                },
                json={
                    'unids': assets
                }
            )

            if 200 <= response.status_code < 300:
                output = response.json()
                print(output)
                return output.get("failed")
            else:
                error_message = f"Error {response.status_code}: {response.text}"
                raise ValueError(error_message)

    @staticmethod
    def get_topdesk_assets_by_templates(page_start: int = 0, page_size: int = 1000):
        if page_start < 0:
            raise ValueError("page_start must be >= 0")
        if not (0 <= page_size <= 1000):
            raise ValueError("page_size must be between 0 and 1000")

        response = requests.get(
            url="https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets",
            auth=(Config.topdesk_username, Config.topdesk_password),
            headers={"Accept": "application/x.topdesk-am-assets-v2+json"},
            params={
                "$filter": (
                    "templateId in ["
                    f"'{Config.topdesk_computer_category_id}',"
                    f"'{Config.topdesk_mobile_category_id}',"
                    f"'{Config.topdesk_device_category_id}'"
                    "]"
                ),
                "pageStart": page_start,
                "pageSize": page_size,
                "archived": False
            }
        )

        if 200 <= response.status_code < 300:
            return response.json()
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            print(error_message)
            raise ValueError(error_message)

    @staticmethod
    def get_topdesk_asset_by_name(asset: IntuneDevice):
        response = requests.get(
            url=        f"https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets",
            auth=       (Config.topdesk_username, Config.topdesk_password),
            headers=    {"Accept": "application/x.topdesk-am-assets-v2+json"},
            params=     {"$filter": f"name eq '{asset.topdesk_asset_id}'"}
        )

        if 200 <= response.status_code < 300:
            return response.json()
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            print(error_message)
            raise ValueError(error_message)

    @staticmethod
    def create_topdesk_asset(asset: IntuneDevice):
        response = requests.post(
            url=        f"https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets",
            auth=       (Config.topdesk_username, Config.topdesk_password),
            headers=    {'Content-Type': 'application/json'},
            json=       asset.to_json()
        )

        if 200 <= response.status_code < 300:
            return
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            print(error_message)
            raise ValueError(error_message)

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
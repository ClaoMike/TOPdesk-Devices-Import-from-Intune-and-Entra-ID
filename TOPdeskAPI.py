from Config import Config
import requests
from IntuneDevice import IntuneDevice

class TOPdeskAPI:

    # Create -----------------------------------------------------------------------------------------------------------
    @staticmethod
    def create_topdesk_asset(asset: IntuneDevice):
        response = requests.post(
            url=f"https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets",
            auth=(Config.topdesk_username, Config.topdesk_password),
            headers={'Content-Type': 'application/json'},
            json=asset.to_json()
        )

        if 200 <= response.status_code < 300:
            return response.json()
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            print(error_message)
            print(asset.to_json())
            raise ValueError(error_message)

    # Read -----------------------------------------------------------------------------------------------------------
    @staticmethod
    def get_topdesk_assets_by_templates(page_start: int = 0, page_size: int = 1000, names=None, ids=None, fields=None):
        if page_start < 0:
            raise ValueError("page_start must be >= 0")
        if not (1 <= page_size <= 1000):
            raise ValueError("page_size must be between 1 and 1000")

        body = {
            "templateId": [
                Config.topdesk_computer_category_id,
                Config.topdesk_mobile_category_id,
                Config.topdesk_device_category_id
            ],
            "pageStart": page_start,
            "pageSize": page_size,
            "fetchData": True
        }

        filters = []

        if names:
            filters.extend(
                f"name eq '{TOPdeskAPI.__esc(x)}'"
                for x in names
            )

        if ids:
            filters.extend(
                f"unid eq '{TOPdeskAPI.__esc(x)}'"
                for x in ids
            )

        if filters:
            body["$filter"] = " or ".join(filters)

        if fields:
            body["fields"] = fields

        response = requests.post(
            url="https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets/filter",
            auth=(Config.topdesk_username, Config.topdesk_password),
            headers={
                "Accept": "application/x.topdesk-am-assets-v2+json",
                "Content-Type": "application/json",
            },
            json=body
        )

        if 200 <= response.status_code < 300:
            return response.json()

        error_message = f"Error {response.status_code}: {response.text}"
        print(error_message)
        raise ValueError(error_message)

    @staticmethod
    def get_topdesk_user_id_by_mainframe(user_id):
        response = requests.get(
            url=f"https://dlfseeds.topdesk.net/tas/api/persons?query=mainframeLoginName=={user_id}",
            auth=(Config.topdesk_username, Config.topdesk_password),
            headers={'Content-Type': 'application/json'}
        )

        if 200 <= response.status_code < 300:
            if response.text != '':
                if len(response.json()) == 0:
                    return None
                print(f"Found: {response.json()}")
                person_card = response.json()[0]
                if person_card.get('status') != 'personArchived':
                    return person_card.get('id')
                else:
                    return None
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            raise ValueError(error_message)

    @staticmethod
    def get_asset_assignments(asset_id):
        response = requests.get(
            url=f"https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets/{asset_id}/assignments",
            auth=(Config.topdesk_username, Config.topdesk_password),
            headers={'Content-Type': 'application/json'},
        )

        if 200 <= response.status_code < 300:
            try:
                return response.json()
            except:
                return None
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            raise ValueError(error_message)

    # Update -----------------------------------------------------------------------------------------------------------
    @staticmethod
    def update_topdesk_asset(asset_id, device: IntuneDevice):
        response = requests.post(
            url=f"https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets/{asset_id}",
            auth=(Config.topdesk_username, Config.topdesk_password),
            headers={'Content-Type': 'application/json'},
            json=device.to_json()
        )
        if 200 <= response.status_code < 300:
            return response.json()
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            print(error_message)
            print(device.to_json())
            raise ValueError(error_message)

    @staticmethod
    def assign_user(topdesk_person_card_id, topdesk_asset_id):
        response = requests.put(
            url=f"https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets/{topdesk_asset_id}/assignments",
            auth=(Config.topdesk_username, Config.topdesk_password),
            headers={
                'Content-Type': 'application/json'
            },
            json={
                "linkToId": topdesk_person_card_id,
                "linkType": "person"
            }
        )

        if 200 <= response.status_code < 300:
            return
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            raise ValueError(error_message)

    @staticmethod
    def archive_asset(asset_id: str):
        response = requests.post(
            url=f"https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets/{asset_id}/archive",
            auth=(Config.topdesk_username, Config.topdesk_password),
            headers={'Content-Type': 'application/json'},
            json={"reasonId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}
        )

        if 200 <= response.status_code < 300:
            print(f"Archived asset {asset_id}!")
            return
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            raise ValueError(error_message)

    @staticmethod
    def unarchive_asset(asset_id: str):
        response = requests.post(
            url=f"https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets/{asset_id}/unarchive",
            auth=(Config.topdesk_username, Config.topdesk_password),
            headers={'Content-Type': 'application/json'},
            json={"reasonId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}
        )

        if 200 <= response.status_code < 300:
            print(f"Unarchived asset {asset_id}!")
            return
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            raise ValueError(error_message)

    # Delete -----------------------------------------------------------------------------------------------------------
    @staticmethod
    def delete_assets(assets):
        if len(assets) != 0:
            print(f"Deleting {len(assets)} assets")

            response = requests.post(
                url=        f"https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets/delete",
                auth=       (Config.topdesk_username, Config.topdesk_password),
                headers=    {'Content-Type': 'application/json'},
                json=       {'unids': assets}
            )

            if 200 <= response.status_code < 300:
                output = response.json()
                return output.get("failed")
            else:
                error_message = f"Error {response.status_code}: {response.text}"
                raise ValueError(error_message)

    @staticmethod
    def remove_asset_assignment_person(asset_id, link_id):
        response = requests.delete(
            url=f"https://dlfseeds.topdesk.net/tas/api/assetmgmt/assets/{asset_id}/assignments/{link_id}",
            auth=(Config.topdesk_username, Config.topdesk_password),
            headers={
                'Content-Type': 'application/json'
            },
        )

        if 200 <= response.status_code < 300:
            print("Successfully deleted the assignment link!")
        else:
            error_message = f"Error {response.status_code}: {response.text}"
            raise ValueError(error_message)

    # Internal ---------------------------------------------------------------------------------------------------------
    def __esc(s: str) -> str:
        return str(s).replace("'", "''")

    # ------------------------------------------------------------------------------------------------------------------
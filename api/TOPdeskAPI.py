from system.Config import Config
import requests
from devices.TOPdeskAsset import TOPdeskAsset

import time
import socket
from requests.exceptions import ConnectionError, Timeout, RequestException

class TOPdeskAPI:
    __host = "dlfseeds.topdesk.net"

    # Create -----------------------------------------------------------------------------------------------------------
    @staticmethod
    def create_topdesk_asset(asset: TOPdeskAsset, max_attempts: int = 5):
        response = TOPdeskAPI.__request_with_retry(
            method="POST",
            endpoint="/tas/api/assetmgmt/assets",
            max_attempts=max_attempts,
            headers={"Content-Type": "application/json"},
            json=asset.to_json()
        )
        return response.json()

    # Read -----------------------------------------------------------------------------------------------------------
    @staticmethod
    def get_topdesk_assets_by_templates(
            page_start: int = 0,
            page_size: int = 1000,
            names=None,
            ids=None,
            fields=None,
            max_attempts: int = 5
    ):
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

        response = TOPdeskAPI.__request_with_retry(
            method="POST",
            endpoint="/tas/api/assetmgmt/assets/filter",
            max_attempts=max_attempts,
            headers={
                "Accept": "application/x.topdesk-am-assets-v2+json",
                "Content-Type": "application/json",
            },
            json=body
        )
        return response.json()

    @staticmethod
    def get_topdesk_user_id_by_mainframe(user_id, max_attempts: int = 5):
        response = TOPdeskAPI.__request_with_retry(
            method="GET",
            endpoint="/tas/api/persons",
            max_attempts=max_attempts,
            headers={"Content-Type": "application/json"},
            params={"query": f"mainframeLoginName=={user_id}"}
        )

        if response.text != "":
            persons = response.json()

            if len(persons) == 0:
                return None

            person_card = persons[0]
            if person_card.get("status") != "personArchived":
                return person_card.get("id")

        return None

    @staticmethod
    def get_asset_assignments(asset_id, max_attempts: int = 5):
        response = TOPdeskAPI.__request_with_retry(
            method="GET",
            endpoint=f"/tas/api/assetmgmt/assets/{asset_id}/assignments",
            max_attempts=max_attempts,
            headers={"Content-Type": "application/json"},
        )

        try:
            return response.json()
        except Exception:
            return None

    # Update -----------------------------------------------------------------------------------------------------------
    @staticmethod
    def update_topdesk_asset(asset_id, device: TOPdeskAsset, max_attempts=5):
        response = TOPdeskAPI.__request_with_retry(
            method="POST",
            endpoint=f"/tas/api/assetmgmt/assets/{asset_id}",
            max_attempts=max_attempts,
            headers={"Content-Type": "application/json"},
            json=device.to_json()
        )
        return response.json()

    @staticmethod
    def assign_user(topdesk_person_card_id, topdesk_asset_id, max_attempts=5):
        TOPdeskAPI.__request_with_retry(
            method="PUT",
            endpoint=f"/tas/api/assetmgmt/assets/{topdesk_asset_id}/assignments",
            max_attempts=max_attempts,
            headers={"Content-Type": "application/json"},
            json={
                "linkToId": topdesk_person_card_id,
                "linkType": "person"
            }
        )

    @staticmethod
    def archive_asset(asset_id: str, max_attempts: int = 5):
        TOPdeskAPI.__request_with_retry(
            method="POST",
            endpoint=f"/tas/api/assetmgmt/assets/{asset_id}/archive",
            max_attempts=max_attempts,
            headers={"Content-Type": "application/json"},
            json={"reasonId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}
        )
        print(f"Archived asset {asset_id}!")

    @staticmethod
    def unarchive_asset(asset_id: str, max_attempts: int = 5):
        TOPdeskAPI.__request_with_retry(
            method="POST",
            endpoint=f"/tas/api/assetmgmt/assets/{asset_id}/unarchive",
            max_attempts=max_attempts,
            headers={"Content-Type": "application/json"},
            json={"reasonId": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}
        )
        print(f"Unarchived asset {asset_id}!")

    # Delete -----------------------------------------------------------------------------------------------------------
    @staticmethod
    def delete_assets(assets, max_attempts: int = 5):
        if len(assets) != 0:
            print(f"Deleting {len(assets)} assets")

            response = TOPdeskAPI.__request_with_retry(
                method="POST",
                endpoint="/tas/api/assetmgmt/assets/delete",
                max_attempts=max_attempts,
                headers={"Content-Type": "application/json"},
                json={"unids": assets}
            )

            output = response.json()
            return output.get("failed")

    @staticmethod
    def remove_asset_assignment_person(asset_id, link_id, max_attempts: int = 5):
        TOPdeskAPI.__request_with_retry(
            method="DELETE",
            endpoint=f"/tas/api/assetmgmt/assets/{asset_id}/assignments/{link_id}",
            max_attempts=max_attempts,
            headers={"Content-Type": "application/json"},
        )
        print("Successfully deleted the assignment link!")

    # Internal ---------------------------------------------------------------------------------------------------------
    @staticmethod
    def __resolve_host(hostname: str) -> str:
        return socket.gethostbyname(hostname)

    @staticmethod
    def __request_with_retry(
            method: str,
            endpoint: str,
            *,
            max_attempts: int = 5,
            timeout: int = 30,
            **kwargs
    ) -> requests.Response:
        """
        Sends an HTTP request to TOPdesk with retry logic for DNS/network errors.

        :param method: HTTP method, e.g. 'GET', 'POST', 'PUT'
        :param endpoint: Path after host, e.g. '/tas/api/persons'
        :param max_attempts: Maximum number of attempts
        :param timeout: Request timeout in seconds
        :param kwargs: Extra arguments passed to requests.request(...)
        :return: requests.Response
        """
        url = f"https://{TOPdeskAPI.__host}{endpoint}"

        for attempt in range(1, max_attempts + 1):
            try:
                ip = TOPdeskAPI.__resolve_host(TOPdeskAPI.__host)
                print(f"[{method} {endpoint}] [Attempt {attempt}] Resolved {TOPdeskAPI.__host} to {ip}")

                response = requests.request(
                    method=method,
                    url=url,
                    auth=(Config.topdesk_username, Config.topdesk_password),
                    timeout=timeout,
                    **kwargs
                )

                response.raise_for_status()
                return response

            except socket.gaierror as e:
                print(f"[{method} {endpoint}] [Attempt {attempt}] DNS resolution failed: {e}")

            except (ConnectionError, Timeout) as e:
                print(f"[{method} {endpoint}] [Attempt {attempt}] Network error: {e}")

            except RequestException as e:
                print(f"[{method} {endpoint}] [Attempt {attempt}] HTTP/application error: {e}")
                raise

            if attempt < max_attempts:
                sleep_seconds = 2 ** attempt
                print(f"[{method} {endpoint}] Retrying in {sleep_seconds} seconds...")
                time.sleep(sleep_seconds)

        raise RuntimeError(f"[{method} {endpoint}] Failed after {max_attempts} attempts")

    @staticmethod
    def __esc(s: str) -> str:
        return str(s).replace("'", "''")

    # ------------------------------------------------------------------------------------------------------------------
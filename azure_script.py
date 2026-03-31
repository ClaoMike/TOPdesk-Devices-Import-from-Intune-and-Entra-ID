import requests
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass
from typing import Any, Callable, Optional
import time
import socket
from requests.exceptions import ConnectionError, Timeout, RequestException
from itertools import chain

from system import automationassets # dev
# import automationassets # prod

########################################################################################################################

class Config:
    tenant_id = None
    client_id = None
    client_secret = None

    topdesk_username = None
    topdesk_password = None

    topdesk_computer_category_id = None
    topdesk_mobile_category_id = None
    topdesk_device_category_id = None

    lenovo_client_id = None

    @staticmethod
    def load():
        cred = automationassets.get_automation_credential("CREDENTIAL_TOPDESK_API")
        Config.topdesk_username = cred["username"]
        Config.topdesk_password = cred["password"]

        Config.topdesk_computer_category_id =   automationassets.get_automation_variable("TOPDESK_COMPUTER_CATEGORY_ID")
        Config.topdesk_mobile_category_id =     automationassets.get_automation_variable("TOPDESK_MOBILE_CATEGORY_ID")
        Config.topdesk_device_category_id =     automationassets.get_automation_variable("TOPDESK_DEVICE_CATEGORY_ID")

        Config.tenant_id =                      automationassets.get_automation_variable("INTUNE_TENANT_ID")
        Config.client_id =                      automationassets.get_automation_variable("INTUNE_CLIENT_ID")
        Config.client_secret =                  automationassets.get_automation_variable("INTUNE_CLIENT_SECRET")

        Config.lenovo_client_id =               automationassets.get_automation_variable("LENOVO_CLIENT_ID")

########################################################################################################################

class Settings:
    FETCH_AZURE_DEVICES = True
    FETCH_INTUNE_DEVICES = True
    FETCH_MICROSOFT_DEFENDER_DEVICES = True

    FETCH_All_AZURE_DEVICES = True
    FETCH_All_INTUNE_DEVICES = True

    NUMBER_OF_DEVICES_PAGES_ALLOWED_FOR_FETCHING = 1

    DELETE_OUTDATED_TOPDESK_ASSETS = True
    DEVICES_PER_FETCHED_PAGE = 100 # should be 1000 for lenovo compliance

########################################################################################################################

@dataclass(frozen=True)
class FieldCheck:
    label: str
    left: Callable[[], Any]                 # value from IntuneDevice (or computed)
    right: Callable[[], Any]                # value from TOPdesk dict (or computed)
    normalize: Optional[Callable[[Any], Any]] = None  # optional normalization for both sides

########################################################################################################################

class DeviceSource(Enum):
    INTUNE = 1
    AZURE = 2

########################################################################################################################

class TOPdeskAsset:
    def __init__(self, source: DeviceSource, data: dict):
        self.__source = source

        if self.__source == DeviceSource.INTUNE:
            self.azureADDeviceId                                = data.get("azureADDeviceId")

            azureADRegistered                                   = data.get("azureADRegistered")
            self.__azureADRegistered                            = False if azureADRegistered is None else azureADRegistered

            self.__complianceState                              = data.get("complianceState")
            self.__deviceName                                   = data.get("deviceName")
            self.__enrolledDateTime                             = data.get("enrolledDateTime")
            self.__freeStorageSpaceInBytes                      = data.get("freeStorageSpaceInBytes")
            self.__id                                           = data.get("id")
            self.__isEncrypted                                  = data.get("isEncrypted")
            self.__imei                                         = data.get("imei")
            self.__isSupervised                                 = data.get("isSupervised")
            self.__lastSyncDateTime                             = data.get("lastSyncDateTime")
            self.__managedDeviceOwnerType                       = data.get("managedDeviceOwnerType")
            self.__managementCertificateExpirationDate          = data.get("managementCertificateExpirationDate")
            self.manufacturer                                   = data.get("manufacturer")
            self.model                                        = data.get("model")
            self.__operatingSystem                              = data.get("operatingSystem")
            self.__osVersion                                    = data.get("osVersion")
            self.serialNumber                                   = data.get("serialNumber")
            self.__subscriberCarrier                            = data.get("subscriberCarrier")
            self.__totalStorageSpaceInBytes                     = data.get("totalStorageSpaceInBytes")
            self.userId                                         = data.get("userId")

        elif source == DeviceSource.AZURE:
            self.azureADDeviceId                                = data.get("deviceId")
            self.__id                                           = data.get("id")
            self.__deviceName                                   = data.get("displayName")
            self.manufacturer                                   = data.get("manufacturer")
            self.model                                          = data.get("model")
            self.__operatingSystem                              = data.get("operatingSystem")
            self.__osVersion                                    = data.get("operatingSystemVersion")

            isSupervised                                        = data.get("isManaged")
            self.__isSupervised                                 = False if isSupervised is None else isSupervised

            self.__lastSyncDateTime                             = data.get("approximateLastSignInDateTime")
            self.__enrolledDateTime                             = data.get("registrationDateTime")
            self.userId                                         = data.get("userId")

        # Lenovo data
        # Warranty fields (for Lenovo devices only)
        self.is_in_warranty                                 = None
        self.country                                        = None
        self.lenovo_product_webpage_url                     = None
        self.product_name                                   = None
        self.warranty_expiration_date                       = None
        self.number_of_days_left_until_the_warranty_expires = None

        # Microsoft Defender values
        self.__last_ip_address                              = None
        self.__exposure_level                               = None
        self.__last_external_ip_address                     = None

        # TOPdesk data (computed, not fetched)
        self.__device_type, self.topdesk_asset_id = TOPdeskAsset.generate_topdesk_asset_data(
            source=self.__source, data=data
        )

    def to_json(self):
        # Warranty fields
        warrant_fields_dict = {
            "is-in-warranty":                               self.is_in_warranty,
            "country-warranty":                             self.country,
            "model-provided-by-the-manufacturer":           self.product_name,
            "warranty-expiration-date":                     self.warranty_expiration_date,
            "number-of-days-until-the-warranty-expires":    self.number_of_days_left_until_the_warranty_expires,
            "warranty-url":                                 self.lenovo_product_webpage_url
        }

        # Microsoft Defender data
        microsoft_defender_fields_dict = {
            "exposure-level":                               self.__exposure_level,
            "last-ip-address":                              self.__last_ip_address,
            "last-external-ip-address":                     self.__last_external_ip_address
        }

        if self.__source == DeviceSource.INTUNE:
            data_dict = {
                "azure-ad-registered":                          self.__azureADRegistered,
                "compliance-status":                            self.__complianceState,
                "free-storage":                                 TOPdeskAsset.__bytes_to_gb(bytes_value=self.__freeStorageSpaceInBytes),
                "intune-id":                                    self.__id,
                "encrypted":                                    self.__isEncrypted,
                "imei":                                         self.__imei,
                "ownership":                                    self.__managedDeviceOwnerType,
                "management-certificate-expiration-date":       self.__managementCertificateExpirationDate,
                "serial-number":                                self.serialNumber,
                "subscriber-carrier":                           self.__subscriberCarrier,
                "total-storage":                                TOPdeskAsset.__bytes_to_gb(bytes_value=self.__totalStorageSpaceInBytes)
            }
            data_dict = data_dict | microsoft_defender_fields_dict | warrant_fields_dict
        else:
            data_dict = {}

        # common fields for both Intune and Azure devices
        data_dict["azure-id"] = self.azureADDeviceId
        data_dict["enrollment-date"] = self.__enrolledDateTime
        data_dict["ismanaged"] = self.__isSupervised
        data_dict["last-check-in"] = self.__lastSyncDateTime
        data_dict["manufacturer-1"] = self.manufacturer
        data_dict["model-1"] = self.model
        data_dict["name-1"] = self.__deviceName
        data_dict["operating-system"] = self.__operatingSystem
        data_dict["os-version"] = self.__osVersion
        data_dict["name"] =self.topdesk_asset_id
        data_dict["type_id"] = OSClassifier.get_device_template(self.__device_type)
        data_dict["user-id"] = self.userId

        return data_dict

    def requiresUpdate(self, target: dict) -> bool:
        asset_id = getattr(self, "topdesk_asset_id", None)

        azure_checks = [
            # None at the moment
        ]

        intune_checks = [
            FieldCheck("azureADRegistered / azure-ad-registered",
                       lambda: self.__azureADRegistered,
                       lambda: target.get("azure-ad-registered")),

            FieldCheck("complianceState / compliance-status",
                       lambda: self.__complianceState,
                       lambda: target.get("compliance-status")),

            FieldCheck("freeStorageSpaceInBytes(GB) / free-storage",
                       lambda: self.__bytes_to_gb(self.__freeStorageSpaceInBytes),
                       lambda: target.get("free-storage")),

            FieldCheck("intuneId / intune-id",
                       lambda: self.__id,
                       lambda: target.get("intune-id")),

            FieldCheck("isEncrypted / encrypted",
                       lambda: self.__isEncrypted,
                       lambda: target.get("encrypted")),

            FieldCheck("imei / imei",
                       lambda: self.__imei,
                       lambda: target.get("imei")),

            FieldCheck("ownership / ownership",
                       lambda: self.__managedDeviceOwnerType,
                       lambda: target.get("ownership")),

            FieldCheck("managementCertExpiry / management-certificate-expiration-date",
                       lambda: self.__managementCertificateExpirationDate,
                       lambda: target.get("management-certificate-expiration-date"),
                       normalize=self.__normalize_date),

            FieldCheck("serialNumber / serial-number",
                       lambda: self.serialNumber,
                       lambda: target.get("serial-number")),

            FieldCheck("subscriberCarrier / subscriber-carrier",
                       lambda: self.__subscriberCarrier,
                       lambda: target.get("subscriber-carrier")),

            FieldCheck("totalStorageSpaceInBytes(GB) / total-storage",
                       lambda: self.__bytes_to_gb(self.__totalStorageSpaceInBytes),
                       lambda: target.get("total-storage")),
        ]

        microsoft_defender_checks = [
            # Microsoft Defender
            FieldCheck("exposure_level / exposure-level",
                       lambda: self.__exposure_level,
                       lambda: target.get("exposure-level")),

            FieldCheck("last_ip_address / last-ip-address",
                       lambda: self.__last_ip_address,
                       lambda: target.get("last-ip-address")),

            FieldCheck("last_external_ip_address / last-external-ip-address",
                       lambda: self.__last_external_ip_address,
                       lambda: target.get("last-external-ip-address")),
        ]

        lenovo_checks = [
            # Lenovo
            FieldCheck("is_in_warranty / is-in-warranty",
                       lambda: self.is_in_warranty,
                       lambda: target.get("is-in-warranty")),

            FieldCheck("country / country-warranty",
                       lambda: self.country,
                       lambda: target.get("country-warranty")),

            FieldCheck("product_name / model-provided-by-the-manufacturer",
                       lambda: self.product_name,
                       lambda: target.get("model-provided-by-the-manufacturer")),

            FieldCheck("warranty_expiration_date / warranty-expiration-date",
                       lambda: self.warranty_expiration_date,
                       lambda: target.get("warranty-expiration-date"),
                       normalize=self.__normalize_date),

            FieldCheck("days_left_warranty / number-of-days-until-the-warranty-expires",
                       lambda: self.number_of_days_left_until_the_warranty_expires,
                       lambda: target.get("number-of-days-until-the-warranty-expires")),

            FieldCheck("lenovo_url / warranty-url",
                       lambda: self.lenovo_product_webpage_url,
                       lambda: target.get("warranty-url"))
        ]

        checks = [
            FieldCheck("azureADDeviceId / azure-id",
                       lambda: self.azureADDeviceId,
                       lambda: target.get("azure-id")),

            FieldCheck("deviceName / name-1",
                       lambda: self.__deviceName,
                       lambda: target.get("name-1")),

            FieldCheck("enrolledDateTime / enrollment-date",
                       lambda: self.__enrolledDateTime,
                       lambda: target.get("enrollment-date"),
                       normalize=self.__normalize_date),

            FieldCheck("isSupervised / ismanaged",
                       lambda: self.__isSupervised,
                       lambda: target.get("ismanaged")),

            FieldCheck("lastSyncDateTime / last-check-in",
                       lambda: self.__lastSyncDateTime,
                       lambda: target.get("last-check-in"),
                       normalize=self.__normalize_date),

            FieldCheck("manufacturer / manufacturer-1",
                       lambda: self.manufacturer,
                       lambda: target.get("manufacturer-1")),

            FieldCheck("model / model-1",
                       lambda: self.model,
                       lambda: target.get("model-1")),

            FieldCheck("operatingSystem / operating-system",
                       lambda: self.__operatingSystem,
                       lambda: target.get("operating-system")),

            FieldCheck("osVersion / os-version",
                       lambda: self.__osVersion,
                       lambda: target.get("os-version")),

            FieldCheck("userId / user-id",
                       lambda: self.userId,
                       lambda: target.get("user-id"))
        ]

        if self.__source == DeviceSource.INTUNE:
            checks.extend(chain(
                intune_checks,
                lenovo_checks,
                microsoft_defender_checks
            ))
        else: # we are checking azure devices
            checks.extend(chain(
                azure_checks
            ))

        mismatches: list[tuple[str, Any, Any]] = []

        for c in checks:
            a = c.left()
            b = c.right()

            if c.normalize is not None:
                a = c.normalize(a)
                b = c.normalize(b)
            else:
                # All other fields: normalize generically
                a = self.__normalize(a)
                b = self.__normalize(b)

            if a != b:
                mismatches.append((c.label, a, b))

        if not mismatches:
            return False  # no update required

        # Print verbose header only when something differs
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("Comparing Intune + Lenovo + Microsoft Defender device with TOPdesk asset")
        print(f"Asset ID: {asset_id}")
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

        for label, a, b in mismatches:
            print(f"[MISMATCH] {label}")
            print(f"  source: {a}")
            print(f"  target: {b}\n")

        return True

    def add_warranty(self, warranty):
        self.is_in_warranty                                 = warranty.get("InWarranty")
        self.country                                        = warranty.get("Country")

        product = warranty.get("Product")
        if product is not None:
            self.lenovo_product_webpage_url = f"https://pcsupport.lenovo.com/us/en/products/{product}/warranty"
            tokens = product.split("/")
            if len(tokens) > 2:
                self.product_name = tokens[2]
            else:
                self.product_name = tokens[-1]
        else:
            self.lenovo_product_webpage_url = None
            self.product_name = None

        self.warranty_expiration_date = None
        latest_warranty_date = datetime.min.replace(tzinfo=timezone.utc)
        warranties = warranty.get("Warranty")
        if warranties is not None:
            for warranty in warranties:
                end_date = datetime.strptime(warranty["End"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if end_date > latest_warranty_date:
                    latest_warranty_date = end_date
            self.warranty_expiration_date = latest_warranty_date

        current_date = datetime.now(timezone.utc)
        self.number_of_days_left_until_the_warranty_expires = (self.warranty_expiration_date - current_date).days + 1 if bool(self.is_in_warranty) else 0

        self.warranty_expiration_date = self.warranty_expiration_date.isoformat() if self.warranty_expiration_date is not None else None

    def add_microsoft_defender_data(self, data):
        self.__operatingSystem          = data.get("osPlatform")
        self.__osVersion                = data.get("version")
        self.__exposure_level           = data.get("exposureLevel")
        self.__last_ip_address          = data.get("lastIpAddress")
        self.__last_external_ip_address = data.get("lastExternalIpAddress")

    @staticmethod
    def generate_topdesk_asset_data(source: DeviceSource, data: dict):
        if source == DeviceSource.INTUNE:
            azure_key = "azureADDeviceId"
        else:  # it is an azure device
            azure_key = "deviceId"

        operating_system = data.get("operatingSystem")  # this one is the same for both Azure and Intune
        azure_id = data.get(azure_key)

        # TOPdesk data (computed, not fetched)
        device_type = OSClassifier.get_device_type(operating_system)
        topdesk_asset_id = f"{device_type.value}-{azure_id}"

        return device_type, topdesk_asset_id

    @staticmethod
    def get_fields(source_type: DeviceSource):
        return ",".join(TOPdeskAsset(data={}, source=source_type).to_json().keys())

    # Internal ---------------------------------------------------------------------------------------------------------

    @staticmethod
    def __bytes_to_gb(bytes_value: int, decimals: int = 0) -> str:
        """Convert bytes to decimal gigabytes (GB)."""
        if bytes_value is None:
            return "0.0 GB"
        return f"{round(bytes_value / 1_000_000_000, decimals)} GB"

    @staticmethod
    def __normalize_date(ts: str) -> datetime:
        if ts in (None, ""):
            return None

        ts = ts.strip()

        # Handle "Z" (UTC) from Intune
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))

        # Handle TOPdesk format without timezone
        dt = datetime.fromisoformat(ts)

        return dt.replace(tzinfo=timezone.utc)

    @staticmethod
    def __normalize(value):
        if isinstance(value, str):
            v = value.strip().lower()

            if v in ("true", "false"):
                return v == "true"

            if v in ("True", "False"):
                return v == "True"

            if isinstance(value, bool):
                return value

            if v.isdigit():
                return int(v)

            return v

        return value

    # ------------------------------------------------------------------------------------------------------------------

########################################################################################################################

class MicrosoftGraphAPI:
    graph_scope_url = 'https://graph.microsoft.com/.default'
    securitycenter_scope_url = 'https://api.securitycenter.microsoft.com/.default'

    @staticmethod
    def get_security_center_access_token():
        return MicrosoftGraphAPI.__get_access_token(scope=MicrosoftGraphAPI.securitycenter_scope_url)

    @staticmethod
    def get_graph_access_token():
        return MicrosoftGraphAPI.__get_access_token(scope=MicrosoftGraphAPI.graph_scope_url)

    @staticmethod
    def get_devices_from_page(page_url, access_token):
        response = requests.get(
            url=page_url,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            },
        )
        if 200 <= response.status_code < 300:
            return response.json().get('value'), response.json().get('@odata.nextLink')
        else:
            raise ValueError(f"Error {response.status_code}: {response.text}")

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

########################################################################################################################

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

########################################################################################################################

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

########################################################################################################################

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
        MicrosoftDefenderAPI.__access_token = MicrosoftGraphAPI.get_security_center_access_token()

########################################################################################################################

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

########################################################################################################################

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

########################################################################################################################

class OSType(Enum):
    COMPUTER = "COMPUTER"
    MOBILE = "MOBILE"
    DEVICE = "DEVICE"

########################################################################################################################

class OSClassifier:
    __computer_os = {
        'Windows',
        'MacMDM',
        'macOS',
        'MacOS'
    }

    __mobile_os = {
        'Android',
        'iOS',
        'AndroidEnterprise',
    }

    @staticmethod
    def get_device_type(os: str):
        if os in OSClassifier.__computer_os:
            return OSType.COMPUTER
        elif os in OSClassifier.__mobile_os:
            return OSType.MOBILE
        else:
            return OSType.DEVICE

    @staticmethod
    def get_device_template(type: OSType):
        if type is OSType.COMPUTER:
            return Config.topdesk_computer_category_id
        elif type is OSType.MOBILE:
            return Config.topdesk_mobile_category_id
        else:
            return Config.topdesk_device_category_id

########################################################################################################################

class TOPdesk:
    __microsoft_defender_devices = dict()

    # Public -----------------------------------------------------------------------------------------------------------
    @staticmethod
    def create_topdesk_assets(current_page_devices, source_type: DeviceSource):
        # get all ids of active devices from TOPdesk
        topdesk_assets_by_name_and_id_dictionary = TOPdesk.__get_topdesk_assets_as_asset_id_and_object_id_dictionary().keys()

        # create a copy, do not remove items while iterating the array
        current_page_devices_copy = current_page_devices.copy()

        devices_to_be_created = []

        # for each device in the current page, create an IntuneDevice object
        # it automatically generates what would be the TOPdesk Asset ID
        for device in current_page_devices_copy:
            local_topdesk_device = TOPdeskAsset(source=source_type, data=device)

            # if the IntuneDevice has an Asset ID that is not present in TOPdesk yet
            if local_topdesk_device.topdesk_asset_id not in topdesk_assets_by_name_and_id_dictionary:
                # we add it to the list of devices that need to be created
                devices_to_be_created.append(local_topdesk_device)

                # we've handled it, so it does not need to be checked for updates
                current_page_devices.remove(device)
        if source_type == DeviceSource.INTUNE:
            TOPdesk.__attach_Lenovo_warranties(devices_to_be_created)
            TOPdesk.__attach_Microsoft_Defender_data(devices_to_be_created)

        if len(devices_to_be_created) > 0:
            print(f"Creating {len(devices_to_be_created)} assets: {[asset.topdesk_asset_id for asset in devices_to_be_created]}")

        # for each intune device that needs to be created
        for local_topdesk_device in devices_to_be_created:
            # create it and save the response - linking to an user requires the new asset ID
            remote_topdesk_asset = TOPdeskAPI.create_topdesk_asset(local_topdesk_device)
            # assign the user to it, if any
            TOPdesk.__assign_user(remote_topdesk_asset)

    @staticmethod
    def update_topdesk_assets(current_page_devices, source_type: DeviceSource):
        local_devices = []

        # create the IntuneDevice instance for each fetched Intune device
        for device in current_page_devices:
            local_devices.append(TOPdeskAsset(source=source_type, data=device))

        # fetch Lenovo data
        TOPdesk.__attach_Lenovo_warranties(local_devices)
        TOPdesk.__attach_Microsoft_Defender_data(local_devices)

        # create a quick access dictionary for intune devices via their topdesk asset id
        local_devices_by_topdesk_asset_id_dictionary = {
            device.topdesk_asset_id: device for device in local_devices
        }

        # get the topdesk assets for each of the above Intune device
        devices_as_topdesk_assets = TOPdesk.__get_topdesk_assets(local_devices_by_topdesk_asset_id_dictionary.keys(), source_type=source_type)

        # compare the fetched Intune device data with the TOPdesk value
        # if they match, do not update
        # otherwise, send update to TOPdesk
        for asset_ID in devices_as_topdesk_assets.keys():
            local_device = local_devices_by_topdesk_asset_id_dictionary.get(asset_ID)
            remote_topdesk_asset = devices_as_topdesk_assets.get(asset_ID)

            if local_device.requiresUpdate(remote_topdesk_asset):
                # first, unarchive it if it is archived
                if remote_topdesk_asset.get('archived'):
                    TOPdeskAPI.unarchive_asset(remote_topdesk_asset.get('unid'))

                # then update
                remote_topdesk_asset = TOPdeskAPI.update_topdesk_asset(
                    asset_id=remote_topdesk_asset.get('unid'),
                    device=local_device
                )

                # finally, assign the user to it, if any
                TOPdesk.__assign_user(remote_topdesk_asset)

    @staticmethod
    def remove_device_assets_except(exceptions):
        # fetch all topdesk assets - their Asset ID and unid only
        topdesk_assets = TOPdesk.__get_topdesk_assets_as_asset_id_and_object_id_dictionary()
        topdesk_assets_copy = topdesk_assets.copy()

        # if the topdesk asset still represents an Intune device, remove it from the list
        for asset in topdesk_assets_copy.keys():
            if asset in exceptions:
                topdesk_assets.pop(asset)

        # remaining assets are not in Intune anymore, so delete them
        topdesk_assets = list(topdesk_assets.values())

        page_start = 0
        page_size = 100
        while True:
            if len(topdesk_assets[page_start:page_start + page_size]) == 0:
                break

            failed = TOPdeskAPI.delete_assets(topdesk_assets[page_start:page_start + page_size])
            page_start += page_size

            # archive the failed ones
            TOPdesk.__filter_out_archived_assets(failed)

            for asset in failed:
                TOPdeskAPI.archive_asset(asset)

    # Internal ---------------------------------------------------------------------------------------------------------

    @staticmethod
    def get_Microsoft_Defender_devices():
        print("Fetching Microsoft Defender Devices")

        MicrosoftDefenderAPI.get_access_token()
        microsoft_defender_devices = MicrosoftDefenderAPI.get_devices()

        for device in microsoft_defender_devices:
            device_id = device.get("aadDeviceId")
            if device_id is not None:
                TOPdesk.__microsoft_defender_devices[device_id] = device

    @staticmethod
    def __attach_Microsoft_Defender_data(intune_devices):
        if len(intune_devices) == 0:
            return

        for device in intune_devices:
            data = TOPdesk.__microsoft_defender_devices.get(device.azureADDeviceId)
            if data is not None:
                device.add_microsoft_defender_data(data)

    @staticmethod
    def __generate_serial_number_to_device_dictionary(devices):
        lenovo_devices_by_serial_number_dictionary = dict()

        for device in devices:
            # quick access for each device via its serial number, if it is a Lenovo device
            if hasattr(device, "manufacturer") and device.manufacturer == "LENOVO":
                if hasattr(device, "serialNumber"):
                    lenovo_devices_by_serial_number_dictionary[device.serialNumber] = device

        return lenovo_devices_by_serial_number_dictionary

    @staticmethod
    def __generate_Lenovo_query_parameters(lenovo_devices_by_serial_number_dictionary: dict):
        serial_params = []

        for serial, device in lenovo_devices_by_serial_number_dictionary.items():
            model = getattr(device, "model", None)

            if model:
                serial_params.append(f"{serial}.{model}")
            else:
                serial_params.append(serial)

        return serial_params

    @staticmethod
    def __fetch_Lenovo_warranties(serial_params):
        warranties = []
        chunk_size = 50

        for i in range(0, len(serial_params), chunk_size):
            chunk = serial_params[i:i + chunk_size]
            params = "Serial=" + "&Serial=".join(chunk)
            print(params)
            warranties.extend(LenovoAPI.get_lenovo_warranties(params))

        return warranties

    @staticmethod
    def __attach_Lenovo_warranties(devices):
        if len(devices) == 0:
            return

        lenovo_devices_by_serial_number_dictionary = TOPdesk.__generate_serial_number_to_device_dictionary(devices)
        if len(lenovo_devices_by_serial_number_dictionary.keys()) == 0:
            return

        print(f"Searching for Lenovo warranties for the following devices: {lenovo_devices_by_serial_number_dictionary.keys()}")
        serial_params = TOPdesk.__generate_Lenovo_query_parameters(lenovo_devices_by_serial_number_dictionary)
        warranties = TOPdesk.__fetch_Lenovo_warranties(serial_params)

        # some fallback values - None should never be returned
        if warranties is None:
            warranties = []
        # this is for cases where only one item is returned, not a list of <more> items
        elif isinstance(warranties, dict):
            warranties = [warranties]
        # trigger an error if there is some unexpected behaviour
        elif not isinstance(warranties, list):
            raise TypeError(f"Unexpected warranties type: {type(warranties)}")

        # attach the warranties
        for warranty in warranties:
            serial_number = warranty.get('Serial')
            device = lenovo_devices_by_serial_number_dictionary[serial_number]

            error_message = warranty.get('ErrorMessage')
            if error_message is not None and error_message != "":
                print(f"Device with TOPdesk asset ID: {device.topdesk_asset_id} and serial number: {serial_number} cannot be found in Lenovo warranty database: {error_message}!")
                continue

            device.add_warranty(warranty)

    @staticmethod
    def __assign_user(topdesk_asset):
        asset_id = topdesk_asset.get('data').get('unid')
        user_id = topdesk_asset.get('data').get('user-id')

        # remove all currently assigned users, if any
        linked_persons = TOPdeskAPI.get_asset_assignments(asset_id).get('persons')
        for person in linked_persons:
            link_id = person.get('linkId')
            TOPdeskAPI.remove_asset_assignment_person(asset_id=asset_id, link_id=link_id)

        # if there is a user ID assigned to the intune device
        if user_id is not None and user_id != '':
            # fetch the topdesk user that has this userID stored inside its mainframe field
            topdesk_user_card_id = TOPdeskAPI.get_topdesk_user_id_by_mainframe(user_id)

            # if there is a match, link the user to the id
            if topdesk_user_card_id is not None:
                TOPdeskAPI.assign_user(topdesk_user_card_id, asset_id)

    @staticmethod
    def __filter_out_archived_assets(failed_to_delete_assets):
        archived = TOPdesk.__get_topdesk_assets_archived_field_only(failed_to_delete_assets)

        failed_set = set(failed_to_delete_assets)
        archived_set = set(archived)

        # Debug: IDs returned as archived that were NOT in failed
        extra = archived_set - failed_set
        if extra:
            print("WARNING: archived returned IDs not in failed (filter ignored?):", list(extra)[:10])

        # Keep only those that are NOT archived
        failed_to_delete_assets[:] = [x for x in failed_to_delete_assets if x not in archived_set]

    @staticmethod
    def __get_topdesk_assets_archived_field_only(ids):
        archived_topdesk_assets = []

        page_start = 0
        page_size = 1000
        while True:
            current_page_assets = TOPdeskAPI.get_topdesk_assets_by_templates(
                page_start=page_start,
                page_size=page_size,
                ids=ids,
                fields='archived'
            ).get("dataSet")

            for asset in current_page_assets:
                if asset.get('archived'):
                    archived_topdesk_assets.append(asset.get('unid'))

            if len(current_page_assets) == 0:
                break

            page_start += page_size

        return archived_topdesk_assets

    @staticmethod
    def __get_topdesk_assets(ids, source_type: DeviceSource):
        topdesk_assets = {}

        page_start = 0
        page_size = 1000
        while True:
            current_page_assets = TOPdeskAPI.get_topdesk_assets_by_templates(
                page_start=page_start,
                page_size=page_size,
                names=ids,
                fields=TOPdeskAsset.get_fields(source_type=source_type)
            ).get("dataSet")

            for asset in current_page_assets:
                topdesk_assets[asset.get('name')] = asset

            if len(current_page_assets) == 0:
                break

            page_start += page_size

        return topdesk_assets

    @staticmethod
    def __get_topdesk_assets_as_asset_id_and_object_id_dictionary():
        topdesk_assets = {}

        page_start = 0
        page_size = 1000
        while True:
            current_page_assets = TOPdeskAPI.get_topdesk_assets_by_templates(page_start=page_start, page_size=page_size).get("dataSet")
            for asset in current_page_assets:
                topdesk_assets[asset.get("text")] = asset.get("id")

            if len(current_page_assets) == 0:
                break

            page_start += page_size

        return topdesk_assets

    # ------------------------------------------------------------------------------------------------------------------

########################################################################################################################

class GraphDeviceProcessor:
    API = None
    SOURCE = None
    INITIAL_URL = None
    FETCH_ALL_FLAG = None
    PAGE_LIMIT_SETTING = "NUMBER_OF_DEVICES_PAGES_ALLOWED_FOR_FETCHING"
    DEVICE_ID_FIELD_FOR_LOGGING = "id"

    @classmethod
    def process_devices(cls):
        cls.API.get_access_token()

        print(f"Fetching {cls.SOURCE.name} Devices")
        next_page = cls.INITIAL_URL

        topdesk_assets_that_must_not_be_deleted = []
        page_counter = 1

        while next_page:
            current_page_devices, next_page = cls.API.get_devices_from_page(next_page)

            print("Page:", page_counter)
            if not getattr(Settings, cls.FETCH_ALL_FLAG):
                if getattr(Settings, cls.PAGE_LIMIT_SETTING) == page_counter:
                    next_page = None
            page_counter += 1

            for device in current_page_devices:
                _, idx = TOPdeskAsset.generate_topdesk_asset_data(
                    source=cls.SOURCE,
                    data=device
                )
                topdesk_assets_that_must_not_be_deleted.append(idx)

            cls.filter_devices(current_page_devices)
            cls.enrich_devices(current_page_devices)

            print(
                f"Found the following {len(current_page_devices)} devices: "
                f"{[device.get(cls.DEVICE_ID_FIELD_FOR_LOGGING) for device in current_page_devices]}"
            )
            TOPdesk.create_topdesk_assets(current_page_devices, source_type=cls.SOURCE)

            print(
                f"Check the following {len(current_page_devices)} devices for any updates: "
                f"{[device.get(cls.DEVICE_ID_FIELD_FOR_LOGGING) for device in current_page_devices]}"
            )
            TOPdesk.update_topdesk_assets(current_page_devices, source_type=cls.SOURCE)

        return topdesk_assets_that_must_not_be_deleted

    @classmethod
    def enrich_devices(cls, current_page_devices):
        pass

    @classmethod
    def filter_devices(cls, current_page_devices):
        pass

########################################################################################################################

class Azure(GraphDeviceProcessor):
    API = AzureAPI
    SOURCE = DeviceSource.AZURE
    INITIAL_URL = (
        f"https://graph.microsoft.com/v1.0/devices"
        f"?$top={Settings.DEVICES_PER_FETCHED_PAGE}"
    )
    FETCH_ALL_FLAG = "FETCH_All_AZURE_DEVICES"
    DEVICE_ID_FIELD_FOR_LOGGING = "deviceId"

    @classmethod
    def enrich_devices(cls, current_page_devices):
        device_ids = {device.get("id"): device for device in current_page_devices}
        users = cls.API.batch_get_registered_users(device_ids)

        for device_id, user in users.items():
            if device_id in device_ids:
                device_ids[device_id]["userId"] = user

    @classmethod
    def filter_devices(cls, current_page_devices):
        current_page_devices[:] = [
            device for device in current_page_devices
            if device.get("managementType") != "MDM"
        ]

########################################################################################################################

class Intune(GraphDeviceProcessor):
    API = IntuneAPI
    SOURCE = DeviceSource.INTUNE
    INITIAL_URL = (
        f"https://graph.microsoft.com/v1.0/deviceManagement/managedDevices"
        f"?$top={Settings.DEVICES_PER_FETCHED_PAGE}"
    )
    FETCH_ALL_FLAG = "FETCH_All_INTUNE_DEVICES"
    DEVICE_ID_FIELD_FOR_LOGGING = "id"

########################################################################################################################

# load config - contains ids and credentials for using various APIs
Config.load()
topdesk_assets_that_must_not_be_deleted = []

# fetch the Microsoft Defender devices at the start, as it sends all devices, no pagination involved
if Settings.FETCH_MICROSOFT_DEFENDER_DEVICES:
    TOPdesk.get_Microsoft_Defender_devices()

# proces the Azure devices
if Settings.FETCH_AZURE_DEVICES:
    processed_devices = Azure.process_devices()
    topdesk_assets_that_must_not_be_deleted.extend(processed_devices)

# proces the Intune devices
if Settings.FETCH_INTUNE_DEVICES:
    processed_devices = Intune.process_devices()
    topdesk_assets_that_must_not_be_deleted.extend(processed_devices)

# delete assets in TOPdesk that are not in Intune anymore
if Settings.DELETE_OUTDATED_TOPDESK_ASSETS:
    TOPdesk.remove_device_assets_except(topdesk_assets_that_must_not_be_deleted)


########################################################################################################################
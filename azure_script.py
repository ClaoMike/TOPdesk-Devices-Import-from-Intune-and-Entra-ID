import requests
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass
from typing import Any, Callable, Optional
import time
import socket
from requests.exceptions import ConnectionError, Timeout, RequestException

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
    FETCH_All_INTUNE_DEVICES = True
    NUMBER_OF_INTUNE_DEVICES_PAGES_ALLOWED_FOR_FETCHING = 1
    DELETE_OUTDATED_TOPDESK_ASSETS = False
    INTUNE_DEVICES_PER_FETCHED_PAGE = 100 # should be 1000 for lenovo compliance

########################################################################################################################

@dataclass(frozen=True)
class FieldCheck:
    label: str
    left: Callable[[], Any]                 # value from IntuneDevice (or computed)
    right: Callable[[], Any]                # value from TOPdesk dict (or computed)
    normalize: Optional[Callable[[Any], Any]] = None  # optional normalization for both sides

########################################################################################################################

class IntuneDevice:
    def __init__(self, dict):
        # Intune data
        self.azureADDeviceId                      = dict.get("azureADDeviceId")
        azureADRegistered = dict.get("azureADRegistered")
        self.__azureADRegistered                    = False if azureADRegistered is None else azureADRegistered
        self.__complianceState                      = dict.get("complianceState")
        self.__deviceName                           = dict.get("deviceName")
        self.__enrolledDateTime                     = dict.get("enrolledDateTime")
        self.__freeStorageSpaceInBytes              = dict.get("freeStorageSpaceInBytes")
        self.__id                                   = dict.get("id")
        self.__isEncrypted                          = dict.get("isEncrypted")
        self.__imei                                 = dict.get("imei")
        self.__isSupervised                         = dict.get("isSupervised")
        self.__lastSyncDateTime                     = dict.get("lastSyncDateTime")
        self.__managedDeviceOwnerType               = dict.get("managedDeviceOwnerType")
        self.__managementCertificateExpirationDate  = dict.get("managementCertificateExpirationDate")
        self.manufacturer                         = dict.get("manufacturer")
        self.__model                                = dict.get("model")
        self.__operatingSystem                      = dict.get("operatingSystem")
        self.__osVersion                            = dict.get("osVersion")
        self.serialNumber                         = dict.get("serialNumber")
        self.__subscriberCarrier                    = dict.get("subscriberCarrier")
        self.__totalStorageSpaceInBytes             = dict.get("totalStorageSpaceInBytes")
        self.userId                                 = dict.get("userId")

        # Lenovo data
        # Warranty fields (for Lenovo devices only)
        self.is_in_warranty = None
        self.country = None
        self.lenovo_product_webpage_url = None
        self.product_name = None
        self.warranty_expiration_date = None
        self.number_of_days_left_until_the_warranty_expires = None

        # Microsoft Defender values
        self.__last_ip_address = None
        self.__exposure_level = None
        self.__last_external_ip_address = None

        # TOPdesk data (computed, not fetched)
        self.__device_type                          = OSClassifier.get_device_type(self.__operatingSystem)
        self.topdesk_asset_id                       = f"{self.__device_type.value}-{self.azureADDeviceId}"

    def to_json(self):
        return {
            "name":                                     self.topdesk_asset_id,
            "type_id":                                  OSClassifier.get_device_template(self.__device_type),

            "azure-id":                                 self.azureADDeviceId,
            "azure-ad-registered":                      self.__azureADRegistered,
            "compliance-status":                        self.__complianceState,
            "name-1":                                   self.__deviceName,
            "enrollment-date":                          self.__enrolledDateTime,
            "free-storage":                             IntuneDevice.__bytes_to_gb(bytes_value=self.__freeStorageSpaceInBytes),
            "intune-id":                                self.__id,
            "encrypted":                                self.__isEncrypted,
            "imei":                                     self.__imei,
            "ismanaged":                                self.__isSupervised,
            "last-check-in":                            self.__lastSyncDateTime,
            "ownership":                                self.__managedDeviceOwnerType,
            "management-certificate-expiration-date":   self.__managementCertificateExpirationDate,
            "manufacturer-1":                           self.manufacturer,
            "model-1":                                  self.__model,
            "operating-system":                         self.__operatingSystem,
            "os-version":                               self.__osVersion,
            "serial-number":                            self.serialNumber,
            "subscriber-carrier":                       self.__subscriberCarrier,
            "total-storage":                            IntuneDevice.__bytes_to_gb(bytes_value=self.__totalStorageSpaceInBytes),
            "user-id":                                  self.userId,

            # Warranty fields
            "is-in-warranty": self.is_in_warranty,
            "country-warranty": self.country,
            "model-provided-by-the-manufacturer": self.product_name,
            "warranty-expiration-date": self.warranty_expiration_date,
            "number-of-days-until-the-warranty-expires": self.number_of_days_left_until_the_warranty_expires,
            "warranty-url": self.lenovo_product_webpage_url,

            # Microsoft Defender data
            "exposure-level": self.__exposure_level,
            "last-ip-address": self.__last_ip_address,
            "last-external-ip-address": self.__last_external_ip_address
        }

    def requiresUpdate(self, target: dict) -> bool:
        asset_id = getattr(self, "topdesk_asset_id", None) or target.get("asset-id")  # adapt to your naming

        checks = [
            FieldCheck("azureADDeviceId / azure-id",
                       lambda: self.azureADDeviceId,
                       lambda: target.get("azure-id")),

            FieldCheck("azureADRegistered / azure-ad-registered",
                       lambda: self.__azureADRegistered,
                       lambda: target.get("azure-ad-registered")),

            FieldCheck("complianceState / compliance-status",
                       lambda: self.__complianceState,
                       lambda: target.get("compliance-status")),

            FieldCheck("deviceName / name-1",
                       lambda: self.__deviceName,
                       lambda: target.get("name-1")),

            FieldCheck("enrolledDateTime / enrollment-date",
                       lambda: self.__enrolledDateTime,
                       lambda: target.get("enrollment-date"),
                       normalize=self.__normalize_date),

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

            FieldCheck("isSupervised / ismanaged",
                       lambda: self.__isSupervised,
                       lambda: target.get("ismanaged")),

            FieldCheck("lastSyncDateTime / last-check-in",
                       lambda: self.__lastSyncDateTime,
                       lambda: target.get("last-check-in"),
                       normalize=self.__normalize_date),

            FieldCheck("ownership / ownership",
                       lambda: self.__managedDeviceOwnerType,
                       lambda: target.get("ownership")),

            FieldCheck("managementCertExpiry / management-certificate-expiration-date",
                       lambda: self.__managementCertificateExpirationDate,
                       lambda: target.get("management-certificate-expiration-date"),
                       normalize=self.__normalize_date),

            FieldCheck("manufacturer / manufacturer-1",
                       lambda: self.manufacturer,
                       lambda: target.get("manufacturer-1")),

            FieldCheck("model / model-1",
                       lambda: self.__model,
                       lambda: target.get("model-1")),

            FieldCheck("operatingSystem / operating-system",
                       lambda: self.__operatingSystem,
                       lambda: target.get("operating-system")),

            FieldCheck("osVersion / os-version",
                       lambda: self.__osVersion,
                       lambda: target.get("os-version")),

            FieldCheck("serialNumber / serial-number",
                       lambda: self.serialNumber,
                       lambda: target.get("serial-number")),

            FieldCheck("subscriberCarrier / subscriber-carrier",
                       lambda: self.__subscriberCarrier,
                       lambda: target.get("subscriber-carrier")),

            FieldCheck("totalStorageSpaceInBytes(GB) / total-storage",
                       lambda: self.__bytes_to_gb(self.__totalStorageSpaceInBytes),
                       lambda: target.get("total-storage")),

            FieldCheck("userId / user-id",
                       lambda: self.userId,
                       lambda: target.get("user-id")),

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
                       lambda: target.get("warranty-url")),

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
    def get_fields():
        return ",".join(IntuneDevice({}).to_json().keys())

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
    @staticmethod
    def get_access_token(scope: str):
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
    def resolve_host(hostname: str) -> str:
        return socket.gethostbyname(hostname)

    @staticmethod
    def update_topdesk_asset(asset_id, device: IntuneDevice, max_attempts=5):
        host = "dlfseeds.topdesk.net"
        url = f"https://{host}/tas/api/assetmgmt/assets/{asset_id}"

        for attempt in range(1, max_attempts + 1):
            try:
                ip = TOPdeskAPI.resolve_host(host)
                print(f"[Attempt {attempt}] Resolved {host} to {ip}")

                response = requests.post(
                    url,
                    auth=(Config.topdesk_username, Config.topdesk_password),
                    headers={'Content-Type': 'application/json'},
                    json=device.to_json(),
                    timeout=30
                )

                response.raise_for_status()
                return response.json()

            except socket.gaierror as e:
                print(f"[Attempt {attempt}] DNS resolution failed for {host}: {e}")

            except (ConnectionError, Timeout) as e:
                print(f"[Attempt {attempt}] Network error while calling TOPdesk: {e}")

            except RequestException as e:
                # This means the request reached the server but failed for another reason
                print(f"[Attempt {attempt}] HTTP/application error: {e}")
                raise

            if attempt < max_attempts:
                sleep_seconds = 2 ** attempt
                print(f"Retrying in {sleep_seconds} seconds...")
                time.sleep(sleep_seconds)

        raise RuntimeError(f"Failed to update TOPdesk asset {asset_id} after {max_attempts} attempts")

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
        MicrosoftDefenderAPI.__access_token = MicrosoftGraphAPI.get_access_token(
            scope='https://api.securitycenter.microsoft.com/.default')

########################################################################################################################

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
        IntuneAPI.__access_token = MicrosoftGraphAPI.get_access_token(
            scope='https://graph.microsoft.com/.default')

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
    def create_topdesk_assets(current_page_devices):
        # get all ids of active devices from TOPdesk
        topdesk_assets_by_name_and_id_dictionary = TOPdesk.__get_topdesk_assets_as_asset_id_and_object_id_dictionary().keys()

        # create a copy, do not remove items while iterating the array
        current_page_devices_copy = current_page_devices.copy()

        intune_devices_to_be_created = []

        # for each device in the current page, create an IntuneDevice object
        # it automatically generates what would be the TOPdesk Asset ID
        for device in current_page_devices_copy:
            intune_device = IntuneDevice(device)

            # if the IntuneDevice has an Asset ID that is not present in TOPdesk yet
            if intune_device.topdesk_asset_id not in topdesk_assets_by_name_and_id_dictionary:
                # we add it to the list of devices that need to be created
                intune_devices_to_be_created.append(intune_device)

                # we've handled it, so it does not need to be checked for updates
                current_page_devices.remove(device)

        TOPdesk.__get_Lenovo_warranties(intune_devices_to_be_created)
        TOPdesk.__attach_Microsoft_Defender_data(intune_devices_to_be_created)

        if len(intune_devices_to_be_created) > 0:
            print(f"Creating {len(intune_devices_to_be_created)} assets: {[asset.topdesk_asset_id for asset in intune_devices_to_be_created]}")

        # for each intune device that needs to be created
        for intune_device in intune_devices_to_be_created:
            # create it and save the response - linking to an user requires the new asset ID
            topdesk_asset = TOPdeskAPI.create_topdesk_asset(intune_device)
            # assign the user to it, if any
            TOPdesk.__assign_user(topdesk_asset)

    @staticmethod
    def update_topdesk_assets(current_page_devices):
        intune_devices = []

        # create the IntuneDevice instance for each fetched Intune device
        for device in current_page_devices:
            intune_devices.append(IntuneDevice(device))

        # fetch Lenovo data
        TOPdesk.__get_Lenovo_warranties(intune_devices)
        TOPdesk.__attach_Microsoft_Defender_data(intune_devices)

        # create a quick access dictionary for intune devices via their topdesk asset id
        intune_devices_by_topdesk_asset_id = {
            device.topdesk_asset_id: device for device in intune_devices
        }

        # get the topdesk assets for each of the above Intune device
        devices_as_topdesk_assets = TOPdesk.__get_topdesk_assets(intune_devices_by_topdesk_asset_id.keys())

        # compare the fetched Intune device data with the TOPdesk value
        # if they match, do not update
        # otherwise, send update to TOPdesk
        for asset_ID in devices_as_topdesk_assets.keys():
            intune_device = intune_devices_by_topdesk_asset_id.get(asset_ID)
            topdesk_asset = devices_as_topdesk_assets.get(asset_ID)

            if intune_device.requiresUpdate(topdesk_asset):
                # first, unarchive it if it is archived
                if topdesk_asset.get('archived'):
                    TOPdeskAPI.unarchive_asset(topdesk_asset.get('unid'))

                # then update
                topdesk_asset = TOPdeskAPI.update_topdesk_asset(
                    asset_id=topdesk_asset.get('unid'),
                    device=intune_device
                )

                # finally, assign the user to it, if any
                TOPdesk.__assign_user(topdesk_asset)

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
    def __get_Lenovo_warranties(intune_devices):
        if len(intune_devices) == 0:
            return

        lenovo_intune_devices_by_serial_number_dictionary = dict()

        for device in intune_devices:
            # quick access for each device via its serial number, if it is a Lenovo device
            if device.manufacturer == "LENOVO":
                lenovo_intune_devices_by_serial_number_dictionary[device.serialNumber] = device

        if len(lenovo_intune_devices_by_serial_number_dictionary.keys()) == 0:
            return

        print(f"Searching for Lenovo warranties for the following devices: {lenovo_intune_devices_by_serial_number_dictionary.keys()}")

        # generate the list of serial numbers as "Serial=...&Serial=..."
        params = "Serial=" + "&Serial=".join(lenovo_intune_devices_by_serial_number_dictionary.keys())
        # fetch Lenovo warranties and stuff
        warranties = LenovoAPI.get_lenovo_warranties(params)

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
            intune_device = lenovo_intune_devices_by_serial_number_dictionary[serial_number]

            error_message = warranty.get('ErrorMessage')
            if error_message is not None and error_message != "":
                print(f"Device with TOPdesk asset ID: {intune_device.topdesk_asset_id} and serial number: {serial_number} cannot be found in Lenovo warranty database: {error_message}!")
                continue

            intune_device.add_warranty(warranty)

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
    def __get_topdesk_assets(ids):
        topdesk_assets = {}

        page_start = 0
        page_size = 1000
        while True:
            current_page_assets = TOPdeskAPI.get_topdesk_assets_by_templates(
                page_start=page_start,
                page_size=page_size,
                names=ids,
                fields=IntuneDevice.get_fields()
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

# load config - contains ids and credentials for using various APIs
Config.load()

# fetch the Microsoft Defender devices at the start, as it sends all devices, no pagination involved
print("Fetching Microsoft Defender Devices")
TOPdesk.get_Microsoft_Defender_devices()

# fetch the Microsoft Graph API access token - not valid forever
IntuneAPI.get_access_token()

print("Fetching Intune Devices")
__intune_url = f"https://graph.microsoft.com/v1.0/deviceManagement/managedDevices?$top={Settings.INTUNE_DEVICES_PER_FETCHED_PAGE}"
next_page = __intune_url

topdesk_assets_that_must_not_be_deleted = []
page_counter = 1

while next_page:
    # fetch a page of intune devices, and the url for the next page
    current_page_devices, next_page = IntuneAPI.get_devices_from_page(next_page)

    # Development Control ----------------------------------------------------------------------------------------------
    print("Page: ", page_counter)
    if not Settings.FETCH_All_INTUNE_DEVICES:
        if Settings.NUMBER_OF_INTUNE_DEVICES_PAGES_ALLOWED_FOR_FETCHING == page_counter:
            next_page = None
    page_counter += 1
    # ----------------------------------------------------------------------------------------------

    # compute and store the topdesk Asset ID of the Intune devices
    for device in current_page_devices:
        topdesk_assets_that_must_not_be_deleted.append(IntuneDevice(device).topdesk_asset_id)

    # create new assets if required
    print(
        f"Found the following {len(current_page_devices)} devices: {[device.get('id') for device in current_page_devices]}")
    TOPdesk.create_topdesk_assets(current_page_devices)

    # current_page_devices contains devices that might need to be updated
    print(
        f"Check the following {len(current_page_devices)} devices for any updates: {[device.get('id') for device in current_page_devices]}")
    TOPdesk.update_topdesk_assets(current_page_devices)

# delete assets in TOPdesk that are not in Intune anymore
if Settings.DELETE_OUTDATED_TOPDESK_ASSETS:
    TOPdesk.remove_device_assets_except(topdesk_assets_that_must_not_be_deleted)

########################################################################################################################
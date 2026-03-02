import requests
from datetime import datetime, timezone
from enum import Enum
from system import automationassets


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

class ApiService:
    # Quick access variables -------------------------------------------------------------------------------------------
    __azure_access_token = None

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

########################################################################################################################

class Settings:
    FETCH_JUST_ONE_PAGE_OF_INTUNE_DEVICES = False
    INTUNE_DEVICES_PER_FETCHED_PAGE = 500

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

class IntuneDevice:
    def __init__(self, dict):
        self.__azureADDeviceId                      = dict.get("azureADDeviceId")
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
        self.__manufacturer                         = dict.get("manufacturer")
        self.__model                                = dict.get("model")
        self.__operatingSystem                      = dict.get("operatingSystem")
        self.__osVersion                            = dict.get("osVersion")
        self.__serialNumber                         = dict.get("serialNumber")
        self.__subscriberCarrier                    = dict.get("subscriberCarrier")
        self.__totalStorageSpaceInBytes             = dict.get("totalStorageSpaceInBytes")
        self.userId                                 = dict.get("userId")

        self.__device_type                          = OSClassifier.get_device_type(self.__operatingSystem)
        self.topdesk_asset_id                       = f"{self.__device_type.value}-{self.__azureADDeviceId}"

    def to_json(self):
        return {
            "name":                                     self.topdesk_asset_id,
            "type_id":                                  OSClassifier.get_device_template(self.__device_type),

            "azure-id":                                 self.__azureADDeviceId,
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
            "manufacturer-1":                           self.__manufacturer,
            "model-1":                                  self.__model,
            "operating-system":                         self.__operatingSystem,
            "os-version":                               self.__osVersion,
            "serial-number":                            self.__serialNumber,
            "subscriber-carrier":                       self.__subscriberCarrier,
            "total-storage":                            IntuneDevice.__bytes_to_gb(bytes_value=self.__totalStorageSpaceInBytes),
            "user-id":                                  self.userId
        }

    def requiresUpdate(self, target: dict) -> bool:
        return not (
                IntuneDevice.__areEqual(
                    self.__azureADDeviceId, target.get("azure-id")
                ) and
                IntuneDevice.__areEqual(
                    self.__azureADRegistered, target.get("azure-ad-registered")
                ) and
                IntuneDevice.__areEqual(
                    self.__complianceState, target.get("compliance-status")
                ) and
                IntuneDevice.__areEqual(
                    self.__deviceName, target.get("name-1")
                ) and
                IntuneDevice.__areEqual(
                    IntuneDevice.__normalize_date(self.__enrolledDateTime) , IntuneDevice.__normalize_date(target.get("enrollment-date"))
                ) and
                IntuneDevice.__areEqual(
                    IntuneDevice.__bytes_to_gb(self.__freeStorageSpaceInBytes), target.get("free-storage")) and
                IntuneDevice.__areEqual(
                    self.__id, target.get("intune-id")
                ) and
                IntuneDevice.__areEqual(
                    self.__isEncrypted, target.get("encrypted")
                ) and
                IntuneDevice.__areEqual(
                    self.__imei, target.get("imei")
                ) and
                IntuneDevice.__areEqual(
                    self.__isSupervised, target.get("ismanaged")
                ) and
                IntuneDevice.__areEqual(
                    IntuneDevice.__normalize_date(self.__lastSyncDateTime), IntuneDevice.__normalize_date(target.get("last-check-in"))
                ) and
                IntuneDevice.__areEqual(
                    self.__managedDeviceOwnerType, target.get("ownership")
                ) and
                IntuneDevice.__areEqual(
                    IntuneDevice.__normalize_date(self.__managementCertificateExpirationDate), IntuneDevice.__normalize_date(target.get("management-certificate-expiration-date"))
                ) and
                IntuneDevice.__areEqual(
                    self.__manufacturer, target.get("manufacturer-1")
                ) and
                IntuneDevice.__areEqual(
                    self.__model, target.get("model-1")
                ) and
                IntuneDevice.__areEqual(
                    self.__operatingSystem, target.get("operating-system")
                ) and
                IntuneDevice.__areEqual(
                    self.__osVersion, target.get("os-version")
                ) and
                IntuneDevice.__areEqual(
                    self.__serialNumber, target.get("serial-number")
                ) and
                IntuneDevice.__areEqual(
                    self.__subscriberCarrier, target.get("subscriber-carrier")
                ) and
                IntuneDevice.__areEqual(
                    IntuneDevice.__bytes_to_gb(self.__totalStorageSpaceInBytes), target.get("total-storage")
                ) and
                IntuneDevice.__areEqual(
                    self.userId, target.get("user-id")
                )
        )

    @staticmethod
    def get_fields():
        return ",".join(IntuneDevice({}).to_json().keys())

    # Internal ---------------------------------------------------------------------------------------------------------
    @staticmethod
    def __areEqual(a, b) -> bool:
        if a != b:
            print("Comparing Intune vs. TOPdesk values")
            print(f"Comparing {a} vs. {b}\n")
        return a == b

    @staticmethod
    def __bytes_to_gb(bytes_value: int, decimals: int = 0) -> str:
        """Convert bytes to decimal gigabytes (GB)."""
        if bytes_value is None:
            return "0.0 GB"
        return f"{round(bytes_value / 1_000_000_000, decimals)} GB"

    @staticmethod
    def __normalize_date(ts: str) -> datetime:
        ts = ts.strip()

        # Handle "Z" (UTC) from Intune
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))

        # Handle TOPdesk format without timezone
        dt = datetime.fromisoformat(ts)

        return dt.replace(tzinfo=timezone.utc)

    # ------------------------------------------------------------------------------------------------------------------

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

########################################################################################################################

class TOPdesk:
    # Public -----------------------------------------------------------------------------------------------------------
    @staticmethod
    def create_topdesk_assets(current_page_devices):
        topdesk_assets_by_name_and_id_dictionary = TOPdesk.__get_topdesk_assets_as_asset_id_and_object_id_dictionary().keys()

        # create a copy, do not remove items while iterating the array
        current_page_devices_copy = current_page_devices.copy()

        # for each device in the current page, create an IntuneDevice object
        # it automatically generates what would be the TOPdesk Asset ID
        for device in current_page_devices_copy:
            intune_device = IntuneDevice(device)

            # if the IntuneDevice has an Asset ID that is not present in TOPdesk yet, we must create the asset
            if intune_device.topdesk_asset_id not in topdesk_assets_by_name_and_id_dictionary:
                # create and save the response
                topdesk_asset = TOPdeskAPI.create_topdesk_asset(intune_device)
                # assign the user to it, if any
                TOPdesk.__assign_user(topdesk_asset)

                # we've handled it, so it does not need to be checked for updates
                current_page_devices.remove(device)

    @staticmethod
    def update_topdesk_assets(current_page_devices):
        intune_devices = {}
        # crate the IntuneDevice instance for each fetched Intune device and add it to a dictionary, where
        # the key is its topdesk asset ID and the value is the object itself
        for device in current_page_devices:
            intune_device = IntuneDevice(device)
            intune_devices[intune_device.topdesk_asset_id] = intune_device

        # get the topdesk assets for each of the above Intune device
        devices_as_topdesk_assets = TOPdesk.__get_topdesk_assets(intune_devices.keys())

        # compare the fetched Intune device data with the TOPdesk value
        # if they match, do not update
        # otherwise, send update to TOPdesk
        for asset_ID in devices_as_topdesk_assets.keys():
            intune_device = intune_devices.get(asset_ID)
            topdesk_asset = devices_as_topdesk_assets.get(asset_ID)

            if intune_device.requiresUpdate(topdesk_asset):
                print(f'Asset {asset_ID} requires an update!')
                print()
                print(intune_device.to_json())
                print(topdesk_asset)
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
        archived_topdesk_assets = TOPdesk.__get_topdesk_assets_archived_field_only(failed_to_delete_assets)
        for asset in archived_topdesk_assets:
            failed_to_delete_assets.remove(asset)

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

# fetch the Microsoft Graph API access token - not valid forever
ApiService.get_azure_access_token()

__intune_url = f"https://graph.microsoft.com/v1.0/deviceManagement/managedDevices?$top={Settings.INTUNE_DEVICES_PER_FETCHED_PAGE}"
next_page = __intune_url

topdesk_assets_that_must_not_be_deleted = []
while next_page:
    # fetch a page of intune devices, and the url for the next page
    current_page_devices, next_page = ApiService.get_devices_from_page(next_page)

    # compute and store the topdesk Asset ID of the Intune devices
    for device in current_page_devices:
        topdesk_assets_that_must_not_be_deleted.append(IntuneDevice(device).topdesk_asset_id)

    # create new assets if required
    TOPdesk.create_topdesk_assets(current_page_devices)

    # current_page_devices contains devices that might need to be updated
    TOPdesk.update_topdesk_assets(current_page_devices)

    ### Load just one page of Intune devices when in development
    if Settings.FETCH_JUST_ONE_PAGE_OF_INTUNE_DEVICES:
        next_page = None

# delete assets in TOPdesk that are not in Intune anymore
TOPdesk.remove_device_assets_except(topdesk_assets_that_must_not_be_deleted)

########################################################################################################################
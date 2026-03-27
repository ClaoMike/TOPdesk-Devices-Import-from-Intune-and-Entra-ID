from devices.os.OSClassifier import OSClassifier
from datetime import datetime, timezone
from devices.FieldCheck import FieldCheck
from typing import Any
from devices.DeviceSource import DeviceSource

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
            self.__model                                        = data.get("model")
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
            self.__model                                        = data.get("model")
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
        else:
            data_dict = {}

        # common fields for both Intune and Azure devices
        data_dict["azure-id"] = self.azureADDeviceId
        data_dict["enrollment-date"] = self.__enrolledDateTime
        data_dict["ismanaged"] = self.__isSupervised
        data_dict["last-check-in"] = self.__lastSyncDateTime
        data_dict["manufacturer-1"] = self.manufacturer
        data_dict["model-1"] = self.__model
        data_dict["name-1"] = self.__deviceName
        data_dict["operating-system"] = self.__operatingSystem
        data_dict["os-version"] = self.__osVersion
        data_dict["name"] =self.topdesk_asset_id
        data_dict["type_id"] = OSClassifier.get_device_template(self.__device_type)
        data_dict["user-id"] = self.userId

        merged_dict = data_dict | warrant_fields_dict | microsoft_defender_fields_dict

        return merged_dict

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
                       lambda: self.__model,
                       lambda: target.get("model-1")),

            FieldCheck("operatingSystem / operating-system",
                       lambda: self.__operatingSystem,
                       lambda: target.get("operating-system")),

            FieldCheck("osVersion / os-version",
                       lambda: self.__osVersion,
                       lambda: target.get("os-version")),

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

        if self.__source == DeviceSource.INTUNE:
            checks.extend(intune_checks)
        else:
            checks.extend(azure_checks)

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
from devices.os.OSClassifier import OSClassifier
from datetime import datetime, timezone
from devices.FieldCheck import FieldCheck
from typing import Any

class IntuneDevice:
    def __init__(self, dict):
        # Intune data
        self.azureADDeviceId                                = dict.get("azureADDeviceId")

        azureADRegistered = dict.get("azureADRegistered")
        self.__azureADRegistered                            = False if azureADRegistered is None else azureADRegistered

        self.__complianceState                              = dict.get("complianceState")
        self.__deviceName                                   = dict.get("deviceName")
        self.__enrolledDateTime                             = dict.get("enrolledDateTime")
        self.__freeStorageSpaceInBytes                      = dict.get("freeStorageSpaceInBytes")
        self.__id                                           = dict.get("id")
        self.__isEncrypted                                  = dict.get("isEncrypted")
        self.__imei                                         = dict.get("imei")
        self.__isSupervised                                 = dict.get("isSupervised")
        self.__lastSyncDateTime                             = dict.get("lastSyncDateTime")
        self.__managedDeviceOwnerType                       = dict.get("managedDeviceOwnerType")
        self.__managementCertificateExpirationDate          = dict.get("managementCertificateExpirationDate")
        self.manufacturer                                   = dict.get("manufacturer")
        self.__model                                        = dict.get("model")
        self.__operatingSystem                              = dict.get("operatingSystem")
        self.__osVersion                                    = dict.get("osVersion")
        self.serialNumber                                   = dict.get("serialNumber")
        self.__subscriberCarrier                            = dict.get("subscriberCarrier")
        self.__totalStorageSpaceInBytes                     = dict.get("totalStorageSpaceInBytes")
        self.userId                                         = dict.get("userId")

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
        self.__device_type                                  = OSClassifier.get_device_type(self.__operatingSystem)
        self.topdesk_asset_id                               = f"{self.__device_type.value}-{self.azureADDeviceId}"

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
from OSClassifier import OSClassifier

class IntuneDevice:
    def __init__(self, dict):
        self.__azureADDeviceId                      = dict.get("azureADDeviceId")
        self.__azureADRegistered                    = dict.get("azureADRegistered")
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
        self.__userId                               = dict.get("userId")

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
            "free-storage":                             f"{IntuneDevice.__bytes_to_gb(bytes_value=self.__freeStorageSpaceInBytes)} GB",
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
            "total-storage":                            f"{IntuneDevice.__bytes_to_gb(bytes_value=self.__totalStorageSpaceInBytes)} GB",
            "user-id":                                  self.__userId

            # "last-ip-address": getattr(self, "last_ip_address", None),
            # "exposure-level": getattr(self, "exposure_level", None),
            # "last-external-ip-address": getattr(self, "last_external_ip_address", None),
            # # Warranty fields
            # "is-in-warranty": self.is_in_warranty,
            # "country-warranty": self.country,
            # "model-provided-by-the-manufacturer": self.product_name,
            # "warranty-expiration-date": self.warranty_expiration_date.strftime(
            #     "%Y-%m-%dT%H:%M:%S.000Z") if self.warranty_expiration_date else None,
            # "number-of-days-until-the-warranty-expires": self.number_of_days_left_until_the_warranty_expires,
            # "warranty-url": self.lenovo_product_webpage_url,
        }

    def requiresUpdate(self, target: dict) -> bool:
        # if self.__azureADDeviceId                       != target.get("azure-id"):
        #     return False
        #
        # if self.__azureADRegistered                     != target.get("azure-ad-registered"):
        #     return False
        #
        # if self.__complianceState                       != target.get("compliance-status"):
        #     return False
        #
        # if self.__deviceName                            != target.get("name-1"):
        #     return False
        #
        # if self.__enrolledDateTime                      != target.get("enrollment-date"):
        #     return False
        #
        # if self.__freeStorageSpaceInBytes               != target.get("free-storage"):
        #     return False
        #
        # if self.__id                                    != target.get("intune-id"):
        #     return False
        #
        # if self.__isEncrypted                           != target.get("encrypted"):
        #     return False
        #
        # if self.__imei                                  != target.get("imei"):
        #     return False
        #
        # if self.__isSupervised                          != target.get("ismanaged"):
        #     return False
        #
        # if self.__lastSyncDateTime                      != target.get("last-check-in"):
        #     return False
        #
        # if self.__managedDeviceOwnerType                != target.get("ownership"):
        #     return False
        #
        # if self.__managementCertificateExpirationDate   != target.get("management-certificate-expiration-date"):
        #     return False
        #
        # if self.__manufacturer                          != target.get("manufacturer-1"):
        #     return False
        #
        # if self.__model                                 != target.get("model-1"):
        #     return False
        #
        # if self.__operatingSystem                       != target.get("operating-system"):
        #     return False
        #
        # if self.__osVersion                             != target.get("os-version"):
        #     return False
        #
        # if self.__serialNumber                          != target.get("serial-number"):
        #     return False
        #
        # if self.__subscriberCarrier                     != target.get("subscriber-carrier"):
        #     return False
        #
        # if self.__totalStorageSpaceInBytes              != target.get("total-storage"):
        #     return False
        #
        # if self.__userId                                != target.get("user-id"):
        #     return False

        return not (
                IntuneDevice.__areEqual(self.__azureADDeviceId, target.get("azure-id")) and
                IntuneDevice.__areEqual(self.__azureADRegistered, target.get("azure-ad-registered")) and
                IntuneDevice.__areEqual(self.__complianceState, target.get("compliance-status")) and
                IntuneDevice.__areEqual(self.__deviceName, target.get("name-1")) and
                IntuneDevice.__areEqual(self.__enrolledDateTime, target.get("enrollment-date")) and
                IntuneDevice.__areEqual(self.__freeStorageSpaceInBytes, target.get("free-storage")) and
                IntuneDevice.__areEqual(self.__id, target.get("intune-id")) and
                IntuneDevice.__areEqual(self.__isEncrypted, target.get("encrypted")) and
                IntuneDevice.__areEqual(self.__imei, target.get("imei")) and
                IntuneDevice.__areEqual(self.__isSupervised, target.get("ismanaged")) and
                IntuneDevice.__areEqual(self.__lastSyncDateTime, target.get("last-check-in")) and
                IntuneDevice.__areEqual(self.__managedDeviceOwnerType, target.get("ownership")) and
                IntuneDevice.__areEqual(self.__managementCertificateExpirationDate, target.get("management-certificate-expiration-date")) and
                IntuneDevice.__areEqual(self.__manufacturer, target.get("manufacturer-1")) and
                IntuneDevice.__areEqual(self.__model, target.get("model-1")) and
                IntuneDevice.__areEqual(self.__operatingSystem, target.get("operating-system")) and
                IntuneDevice.__areEqual(self.__osVersion, target.get("os-version")) and
                IntuneDevice.__areEqual(self.__serialNumber, target.get("serial-number")) and
                IntuneDevice.__areEqual(self.__subscriberCarrier, target.get("subscriber-carrier")) and
                IntuneDevice.__areEqual(self.__totalStorageSpaceInBytes, target.get("total-storage")) and
                IntuneDevice.__areEqual(self.__userId, target.get("user-id"))
        )

        # 'unid': 'e032024f-d1aa-41f2-99d2-f779b1201de5'
        # '@@summary': ''
        # '@statusLocked': False
        # 'archived': False
        # '@etag': '2026-02-17T11:49:34.234         '
        # 'type_id': '5F0A918A-1802-412B-A86D-CD4634AE6444'
        # '@status': 'OPERATIONAL'
        # 'modificationDate': '2026-02-17T11:49:34.234'

    @staticmethod
    def __areEqual(a, b) -> bool:
        print("Comparing Intune vs. TOPdesk values")
        print(f"Comparing {a} vs. {b}\n")
        return a==b

    @staticmethod
    def get_fields():
        return ",".join(IntuneDevice({}).to_json().keys())

    def __bytes_to_gb(bytes_value: int, decimals: int = 0) -> float:
        """Convert bytes to decimal gigabytes (GB)."""
        if bytes_value is None:
            return 0.0
        return round(bytes_value / 1_000_000_000, decimals)
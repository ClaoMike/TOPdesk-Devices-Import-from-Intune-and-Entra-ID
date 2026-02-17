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

            "azure_id":                                 self.__azureADDeviceId,
            "azure_ad_registered":                      self.__azureADRegistered,
            "compliance_status":                        self.__complianceState,
            "name_1":                                   self.__deviceName,
            "enrollment_date":                          self.__enrolledDateTime,
            "free_storage":                             self.__freeStorageSpaceInBytes,
            "intune_id":                                self.__id,
            "encrypted":                                self.__isEncrypted,
            "imei":                                     self.__imei,
            "ismanaged":                                self.__isSupervised,
            "last_check_in":                            self.__lastSyncDateTime,
            "ownership":                                self.__managedDeviceOwnerType,
            "management_certificate_expiration_date":   self.__managementCertificateExpirationDate,
            "manufacturer_1":                           self.__manufacturer,
            "model_1":                                  self.__model,
            "operating_system":                         self.__operatingSystem,
            "os_version":                               self.__osVersion,
            "serial_number":                            self.__serialNumber,
            "subscriber_carrier":                       self.__subscriberCarrier,
            "total_storage":                            self.__totalStorageSpaceInBytes,
            "user_id":                                  self.__userId

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


from api.AzureAPI import AzureAPI
from devices.DeviceSource import DeviceSource
from system.Settings import Settings
from platforms.GraphDevicePlatformProcessor import GraphDeviceProcessor

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
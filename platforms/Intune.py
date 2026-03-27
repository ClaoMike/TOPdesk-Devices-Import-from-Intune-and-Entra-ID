from api.IntuneAPI import IntuneAPI
from devices.DeviceSource import DeviceSource
from system.Settings import Settings
from platforms.GraphDevicePlatformProcessor import GraphDeviceProcessor

class Intune(GraphDeviceProcessor):
    API = IntuneAPI
    SOURCE = DeviceSource.INTUNE
    INITIAL_URL = (
        f"https://graph.microsoft.com/v1.0/deviceManagement/managedDevices"
        f"?$top={Settings.DEVICES_PER_FETCHED_PAGE}"
    )
    FETCH_ALL_FLAG = "FETCH_All_INTUNE_DEVICES"
    DEVICE_ID_FIELD_FOR_LOGGING = "id"
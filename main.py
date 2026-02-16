from Config import Config
from ApiService import ApiService
from IntuneDevice import IntuneDevice
from TOPdesk import TOPdesk

Config.load()
ApiService.get_azure_access_token()

topdesk_assets = TOPdesk.get_topdesk_assets()
created_or_updated_devices = []

__intune_url = "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices"
next_page = __intune_url

while next_page:
    current_page_devices, next_page = ApiService.get_devices_from_page(next_page)

    for device in current_page_devices:
        intune_device = IntuneDevice(device)
        if intune_device.topdesk_asset_id not in topdesk_assets.keys(): # if the asset name does not exist
            ApiService.create_topdesk_asset(intune_device) # we create it
            created_or_updated_devices.append(intune_device.topdesk_asset_id)
        else:
            # we (eventually) update
            created_or_updated_devices.append(intune_device.topdesk_asset_id)
            pass

# keep assets that are not in Intune and delete them
TOPdesk.remove_device_assets_except(created_or_updated_devices)

from Config import Config
from ApiService import ApiService
from IntuneDevice import IntuneDevice

Config.load()
ApiService.get_azure_access_token()

devices = []

__intune_url = "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices"
next_page = __intune_url

while next_page:
    current_page_devices, next_page = ApiService.get_devices_from_page(next_page)
    new_counter = 0
    for device in current_page_devices:
        intune_device = IntuneDevice(device)
        matches = ApiService.get_topdesk_asset_by_name(intune_device).get("dataSet")
        if len(matches) == 0:
            ApiService.update_topdesk_asset(intune_device)
            new_counter += 1
        else:
            # update
            pass
    print(f"Created {new_counter}/{len(current_page_devices)}")

        # devices.append(intune_device)

print(len(devices))
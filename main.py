from Config import Config
from ApiService import ApiService
from IntuneDevice import IntuneDevice
from TOPdesk import TOPdesk
from Settings import Settings

# TODO: we need update the Intune devices that need updating
# TODO: we need to link their users as well
# TODO: we need to fetch the Lenovo data
# TODO: we need to fetch the Microsoft Defender data
# TODO: we need to integrate the Azure Entra ID devices as well

# load config - contains ids and credentials for using various APIs
Config.load()

# fetch the Microsoft Graph API access token - not valid forever
ApiService.get_azure_access_token()

# fetch all the topdesk assets (device/computer/mobile) and store their Asset ID, and their TOPdesk ID
topdesk_assets = TOPdesk.get_topdesk_assets()

__intune_url = "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices"
next_page = __intune_url

while next_page:
    # fetch a page of intune devices, and the url for the next page
    current_page_devices, next_page = ApiService.get_devices_from_page(next_page)
    current_page_devices_copy = current_page_devices.copy()

    # for each device in the current page, create an IntuneDevice object
    # it automatically generates what would be the TOPdesk Asset ID
    for device in current_page_devices_copy:
        intune_device = IntuneDevice(device)

        # if the IntuneDevice has an Asset ID that is not present in TOPdesk yet, we must create the asset
        if intune_device.topdesk_asset_id not in topdesk_assets.keys():
            ApiService.create_topdesk_asset(intune_device)
            current_page_devices.remove(device) # we've handled it, so it does not need further processing

    # current_page_devices contains devices that might need to be updated

########################################################################################################################
#### Load just one page of Intune devices when in development ##########################################################
    if Settings.FETCH_JUST_ONE_PAGE_OF_INTUNE_DEVICES:
        next_page = None
########################################################################################################################

# keep assets that are not in Intune and delete them
# TOPdesk.remove_device_assets_except(created_or_updated_devices)

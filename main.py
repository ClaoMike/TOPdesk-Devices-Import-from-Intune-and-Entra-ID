from Config import Config
from ApiService import ApiService
from TOPdesk import TOPdesk
from Settings import Settings
from IntuneDevice import IntuneDevice

# TODO: we need to link their users as well
# TODO: we need to fetch the Lenovo data
# TODO: we need to fetch the Microsoft Defender data
# TODO: we need to integrate the Azure Entra ID devices as well

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

    for device in current_page_devices:
        topdesk_assets_that_must_not_be_deleted.append(IntuneDevice(device).topdesk_asset_id)

    # create new assets if required
    TOPdesk.create_topdesk_assets(current_page_devices)

    # current_page_devices contains devices that might need to be updated
    TOPdesk.update_topdesk_assets(current_page_devices)

    ### Load just one page of Intune devices when in development
    if Settings.FETCH_JUST_ONE_PAGE_OF_INTUNE_DEVICES:
        next_page = None

# keep assets that are not in Intune and delete them
TOPdesk.remove_device_assets_except(topdesk_assets_that_must_not_be_deleted)
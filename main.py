from system.Config import Config
from api.IntuneAPI import IntuneAPI
from TOPdesk import TOPdesk
from system.Settings import Settings
from devices.IntuneDevice import IntuneDevice

# TODO #################################################################################################################
# TODO 3. Detect and fix Microsoft Defender not being added ############################################################
# TODO 4. Fix TOPdesk assets deletion bug(s) ###########################################################################
# TODO 5. Put sensible prints and remove the extra long ones - required for errors only ################################
# TODO 6. Refactor #####################################################################################################
# TODO 7. Import Azure Entra ID devices ################################################################################
# TODO #################################################################################################################

# load config - contains ids and credentials for using various APIs
Config.load()

# fetch the Microsoft Defender devices at the start, as it sends all devices, no pagination involved
print("Fetching Microsoft Defender Devices")
TOPdesk.get_Microsoft_Defender_devices()

# fetch the Microsoft Graph API access token - not valid forever
IntuneAPI.get_access_token()

print("Fetching Intune Devices")
__intune_url = f"https://graph.microsoft.com/v1.0/deviceManagement/managedDevices?$top={Settings.INTUNE_DEVICES_PER_FETCHED_PAGE}"
next_page = __intune_url

topdesk_assets_that_must_not_be_deleted = []
page_counter = 1

while next_page:
    # fetch a page of intune devices, and the url for the next page
    current_page_devices, next_page = IntuneAPI.get_devices_from_page(next_page)

    # Development Control ----------------------------------------------------------------------------------------------
    print("Page: ", page_counter)
    if not Settings.FETCH_All_INTUNE_DEVICES:
        if Settings.NUMBER_OF_INTUNE_DEVICES_PAGES_ALLOWED_FOR_FETCHING == page_counter:
            next_page = None
    page_counter += 1
    # ----------------------------------------------------------------------------------------------

    # compute and store the topdesk Asset ID of the Intune devices
    for device in current_page_devices:
        topdesk_assets_that_must_not_be_deleted.append(IntuneDevice(device).topdesk_asset_id)

    # create new assets if required
    print(
        f"Found the following {len(current_page_devices)} devices: {[device.get('id') for device in current_page_devices]}")
    TOPdesk.create_topdesk_assets(current_page_devices)

    # current_page_devices contains devices that might need to be updated
    print(
        f"Check the following {len(current_page_devices)} devices for any updates: {[device.get('id') for device in current_page_devices]}")
    TOPdesk.update_topdesk_assets(current_page_devices)

# delete assets in TOPdesk that are not in Intune anymore
if Settings.DELETE_OUTDATED_TOPDESK_ASSETS:
    TOPdesk.remove_device_assets_except(topdesk_assets_that_must_not_be_deleted)

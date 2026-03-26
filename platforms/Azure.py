from api.AzureAPI import AzureAPI
from devices.TOPdeskAsset import TOPdeskAsset
from system.Settings import Settings
from devices.DeviceSource import DeviceSource
from platforms.TOPdesk import TOPdesk

class Azure:
    @staticmethod
    def process_devices():
        # fetch the Microsoft Graph API access token - not valid forever
        AzureAPI.get_access_token()

        print("Fetching Azure Devices")
        __azure_url = f"https://graph.microsoft.com/v1.0/devices?$top={Settings.DEVICES_PER_FETCHED_PAGE}"
        next_page = __azure_url

        topdesk_assets_that_must_not_be_deleted = []
        page_counter = 1

        while next_page:
            # fetch a page of intune devices, and the url for the next page
            current_page_devices, next_page = AzureAPI.get_devices_from_page(next_page)

            # Development Control ----------------------------------------------------------------------------------------------
            print("Page: ", page_counter)
            if not Settings.FETCH_All_AZURE_DEVICES:
                if Settings.NUMBER_OF_DEVICES_PAGES_ALLOWED_FOR_FETCHING == page_counter:
                    next_page = None
            page_counter += 1

            print(current_page_devices)
            # ----------------------------------------------------------------------------------------------

            # compute and store the topdesk Asset ID of the Intune devices
            for device in current_page_devices:
                _, idx = TOPdeskAsset.generate_topdesk_asset_data(source=DeviceSource.AZURE, data=device)
                topdesk_assets_that_must_not_be_deleted.append(idx)

            # create new assets if required
            print(
                f"Found the following {len(current_page_devices)} devices: {[device.get('id') for device in current_page_devices]}")
            TOPdesk.create_topdesk_assets(current_page_devices, source_type=DeviceSource.AZURE)

            # current_page_devices contains devices that might need to be updated
            # print(
            #     f"Check the following {len(current_page_devices)} devices for any updates: {[device.get('id') for device in current_page_devices]}")
            # TOPdesk.update_topdesk_assets(current_page_devices, source_type=DeviceSource.AZURE)

        return topdesk_assets_that_must_not_be_deleted
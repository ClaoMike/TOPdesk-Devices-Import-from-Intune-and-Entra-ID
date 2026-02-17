from ApiService import ApiService
from TOPdeskAPI import TOPdeskAPI
from IntuneDevice import IntuneDevice

class TOPdesk:

    @staticmethod
    def create_topdesk_assets(current_page_devices):
        # create a copy, do not remove items while iterating the array
        current_page_devices_copy = current_page_devices.copy()

        # for each device in the current page, create an IntuneDevice object
        # it automatically generates what would be the TOPdesk Asset ID
        for device in current_page_devices_copy:
            intune_device = IntuneDevice(device)

            # if the IntuneDevice has an Asset ID that is not present in TOPdesk yet, we must create the asset
            if intune_device.topdesk_asset_id not in TOPdesk.get_topdesk_assets_as_asset_id_and_object_id_dictionary().keys():
                TOPdeskAPI.create_topdesk_asset(intune_device)
                current_page_devices.remove(device)  # we've handled it, so it does not need further processing

    @staticmethod
    def update_topdesk_assets(current_page_devices):
        pass

    @staticmethod
    def get_topdesk_assets_as_asset_id_and_object_id_dictionary():
        topdesk_assets = {}

        page_start = 0
        page_size = 1000
        while True:
            current_page_assets = TOPdeskAPI.get_topdesk_assets_by_templates(page_start=page_start, page_size=page_size).get("dataSet")
            for asset in current_page_assets:
                topdesk_assets[asset.get("text")] = asset.get("id")

            if len(current_page_assets) == 0:
                break

            page_start += page_size

        return topdesk_assets

    @staticmethod
    def remove_device_assets_except(exceptions):
        topdesk_assets = TOPdesk.get_topdesk_assets_as_asset_id_and_object_id_dictionary()
        for asset in exceptions:
            if asset in topdesk_assets.keys():
                topdesk_assets.pop(asset)
        topdesk_assets = list(topdesk_assets.values())

        page_start = 0
        page_size = 100
        while True:
            if len(topdesk_assets[page_start:page_start + page_size]) == 0:
                break

            failed = TOPdeskAPI.delete_assets(topdesk_assets[page_start:page_start + page_size])
            page_start += page_size

            # archive the failed ones
            for asset in failed:
                TOPdeskAPI.archive_asset(asset)
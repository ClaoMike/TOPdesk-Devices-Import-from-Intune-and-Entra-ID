from TOPdeskAPI import TOPdeskAPI
from IntuneDevice import IntuneDevice

class TOPdesk:
    @staticmethod
    def create_topdesk_assets(current_page_devices):
        topdesk_assets_by_name_and_id_dictionary = TOPdesk.__get_topdesk_assets_as_asset_id_and_object_id_dictionary().keys()

        # create a copy, do not remove items while iterating the array
        current_page_devices_copy = current_page_devices.copy()

        # for each device in the current page, create an IntuneDevice object
        # it automatically generates what would be the TOPdesk Asset ID
        for device in current_page_devices_copy:
            intune_device = IntuneDevice(device)

            # if the IntuneDevice has an Asset ID that is not present in TOPdesk yet, we must create the asset
            if intune_device.topdesk_asset_id not in topdesk_assets_by_name_and_id_dictionary:
                TOPdeskAPI.create_topdesk_asset(intune_device)
                current_page_devices.remove(device)  # we've handled it, so it does not need further processing

    @staticmethod
    def update_topdesk_assets(current_page_devices):
        intune_devices = {}
        # crate the IntuneDevice instance for each fetched Intune device and add it to a dictionary, where
        # the key is its topdesk asset ID and the value is the object itself
        for device in current_page_devices:
            intune_device = IntuneDevice(device)
            intune_devices[intune_device.topdesk_asset_id] = intune_device

        # get the topdesk assets for each of the above Intune device
        devices_as_topdesk_assets = TOPdesk.__get_topdesk_assets(intune_devices.keys())

        # compare the fetched Intune device data with the TOPdesk value
        # if they match, do not update
        # otherwise, send update to TOPdesk
        for asset_ID in devices_as_topdesk_assets.keys():
            intune_device = intune_devices.get(asset_ID)
            topdesk_asset = devices_as_topdesk_assets.get(asset_ID)

            if intune_device.requiresUpdate(topdesk_asset):
                print(f'Asset {asset_ID} requires an update!')
                TOPdeskAPI.update_topdesk_asset(
                    template_id=topdesk_asset.get('type_id'),
                    asset_id=topdesk_asset.get('unid'),
                    device=intune_device
                )

    @staticmethod
    def remove_device_assets_except(exceptions):
        # fetch all topdesk assets - their Asset ID and unid only
        topdesk_assets = TOPdesk.__get_topdesk_assets_as_asset_id_and_object_id_dictionary()
        topdesk_assets_copy = topdesk_assets.copy()

        # if the topdesk asset still represents an Intune device, remove it from the list
        for asset in topdesk_assets_copy.keys():
            if asset in exceptions:
                topdesk_assets.pop(asset)

        # remaining assets are not in Intune anymore, so delete them
        topdesk_assets = list(topdesk_assets.values())

        page_start = 0
        page_size = 100
        while True:
            if len(topdesk_assets[page_start:page_start + page_size]) == 0:
                break

            failed = TOPdeskAPI.delete_assets(topdesk_assets[page_start:page_start + page_size])
            page_start += page_size

            # archive the failed ones
            # for asset in failed:
            # TOPdeskAPI.archive_asset(asset)

    @staticmethod
    def __get_topdesk_assets(ids):
        topdesk_assets = {}

        page_start = 0
        page_size = 1000
        while True:
            current_page_assets = TOPdeskAPI.get_topdesk_assets_by_templates(
                page_start=page_start,
                page_size=page_size,
                ids=ids,
                fields=IntuneDevice.get_fields()
            ).get("dataSet")

            for asset in current_page_assets:
                topdesk_assets[asset.get('name')] = asset

            if len(current_page_assets) == 0:
                break

            page_start += page_size

        return topdesk_assets

    @staticmethod
    def __get_topdesk_assets_as_asset_id_and_object_id_dictionary():
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
from TOPdeskAPI import TOPdeskAPI
from IntuneDevice import IntuneDevice

class TOPdesk:
    # Public -----------------------------------------------------------------------------------------------------------
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
                # create and save the response
                topdesk_asset = TOPdeskAPI.create_topdesk_asset(intune_device)
                # assign the user to it, if any
                TOPdesk.__assign_user(topdesk_asset)

                # we've handled it, so it does not need to be checked for updates
                current_page_devices.remove(device)

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
                # first, unarchive it if it is archived
                if topdesk_asset.get('archived'):
                    TOPdeskAPI.unarchive_asset(topdesk_asset.get('unid'))

                # then update
                topdesk_asset = TOPdeskAPI.update_topdesk_asset(
                    asset_id=topdesk_asset.get('unid'),
                    device=intune_device
                )

                # finally, assign the user to it, if any
                TOPdesk.__assign_user(topdesk_asset)

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
            TOPdesk.__filter_out_archived_assets(failed)

            for asset in failed:
                TOPdeskAPI.archive_asset(asset)

    # Internal ---------------------------------------------------------------------------------------------------------

    @staticmethod
    def __assign_user(topdesk_asset):
        asset_id = topdesk_asset.get('data').get('unid')
        user_id = topdesk_asset.get('data').get('user-id')

        # remove all currently assigned users, if any
        linked_persons = TOPdeskAPI.get_asset_assignments(asset_id).get('persons')
        for person in linked_persons:
            link_id = person.get('linkId')
            TOPdeskAPI.remove_asset_assignment_person(asset_id=asset_id, link_id=link_id)

        # if there is a user ID assigned to the intune device
        if user_id is not None and user_id != '':
            # fetch the topdesk user that has this userID stored inside its mainframe field
            topdesk_user_card_id = TOPdeskAPI.get_topdesk_user_id_by_mainframe(user_id)

            # if there is a match, link the user to the id
            if topdesk_user_card_id is not None:
                TOPdeskAPI.assign_user(topdesk_user_card_id, asset_id)

    @staticmethod
    def __filter_out_archived_assets(failed_to_delete_assets):
        archived_topdesk_assets = TOPdesk.__get_topdesk_assets_archived_field_only(failed_to_delete_assets)
        for asset in archived_topdesk_assets:
            failed_to_delete_assets.remove(asset)

    @staticmethod
    def __get_topdesk_assets_archived_field_only(ids):
        archived_topdesk_assets = []

        page_start = 0
        page_size = 1000
        while True:
            current_page_assets = TOPdeskAPI.get_topdesk_assets_by_templates(
                page_start=page_start,
                page_size=page_size,
                ids=ids,
                fields='archived'
            ).get("dataSet")

            for asset in current_page_assets:
                if asset.get('archived'):
                    archived_topdesk_assets.append(asset.get('unid'))

            if len(current_page_assets) == 0:
                break

            page_start += page_size

        return archived_topdesk_assets

    @staticmethod
    def __get_topdesk_assets(ids):
        topdesk_assets = {}

        page_start = 0
        page_size = 1000
        while True:
            current_page_assets = TOPdeskAPI.get_topdesk_assets_by_templates(
                page_start=page_start,
                page_size=page_size,
                names=ids,
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

    # ------------------------------------------------------------------------------------------------------------------
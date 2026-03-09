from api.MicrosoftDefenderAPI import MicrosoftDefenderAPI
from api.TOPdeskAPI import TOPdeskAPI
from devices.IntuneDevice import IntuneDevice
from api.LenovoAPI import LenovoAPI

class TOPdesk:
    __microsoft_defender_devices = dict()

    # Public -----------------------------------------------------------------------------------------------------------
    @staticmethod
    def create_topdesk_assets(current_page_devices):
        # get all ids of active devices from TOPdesk
        topdesk_assets_by_name_and_id_dictionary = TOPdesk.__get_topdesk_assets_as_asset_id_and_object_id_dictionary().keys()

        # create a copy, do not remove items while iterating the array
        current_page_devices_copy = current_page_devices.copy()

        intune_devices_to_be_created = []

        # for each device in the current page, create an IntuneDevice object
        # it automatically generates what would be the TOPdesk Asset ID
        for device in current_page_devices_copy:
            intune_device = IntuneDevice(device)

            # if the IntuneDevice has an Asset ID that is not present in TOPdesk yet
            if intune_device.topdesk_asset_id not in topdesk_assets_by_name_and_id_dictionary:
                # we add it to the list of devices that need to be created
                intune_devices_to_be_created.append(intune_device)

                # we've handled it, so it does not need to be checked for updates
                current_page_devices.remove(device)

        TOPdesk.__get_Lenovo_warranties(intune_devices_to_be_created)
        TOPdesk.__attach_Microsoft_Defender_data(intune_devices_to_be_created)

        if len(intune_devices_to_be_created) > 0:
            print(f"Creating {len(intune_devices_to_be_created)} assets: {[asset.topdesk_asset_id for asset in intune_devices_to_be_created]}")

        # for each intune device that needs to be created
        for intune_device in intune_devices_to_be_created:
            # create it and save the response - linking to an user requires the new asset ID
            topdesk_asset = TOPdeskAPI.create_topdesk_asset(intune_device)
            # assign the user to it, if any
            TOPdesk.__assign_user(topdesk_asset)

    @staticmethod
    def update_topdesk_assets(current_page_devices):
        intune_devices = []

        # create the IntuneDevice instance for each fetched Intune device
        for device in current_page_devices:
            intune_devices.append(IntuneDevice(device))

        # fetch Lenovo data
        TOPdesk.__get_Lenovo_warranties(intune_devices)
        TOPdesk.__attach_Microsoft_Defender_data(intune_devices)

        # create a quick access dictionary for intune devices via their topdesk asset id
        intune_devices_by_topdesk_asset_id = {
            device.topdesk_asset_id: device for device in intune_devices
        }

        # get the topdesk assets for each of the above Intune device
        devices_as_topdesk_assets = TOPdesk.__get_topdesk_assets(intune_devices_by_topdesk_asset_id.keys())

        # compare the fetched Intune device data with the TOPdesk value
        # if they match, do not update
        # otherwise, send update to TOPdesk
        for asset_ID in devices_as_topdesk_assets.keys():
            intune_device = intune_devices_by_topdesk_asset_id.get(asset_ID)
            topdesk_asset = devices_as_topdesk_assets.get(asset_ID)

            if intune_device.requiresUpdate(topdesk_asset):
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
    def get_Microsoft_Defender_devices():
        MicrosoftDefenderAPI.get_access_token()
        microsoft_defender_devices = MicrosoftDefenderAPI.get_devices()

        for device in microsoft_defender_devices:
            device_id = device.get("aadDeviceId")
            if device_id is not None:
                TOPdesk.__microsoft_defender_devices[device_id] = device

    @staticmethod
    def __attach_Microsoft_Defender_data(intune_devices):
        if len(intune_devices) == 0:
            return

        for device in intune_devices:
            data = TOPdesk.__microsoft_defender_devices.get(device.azureADDeviceId)
            if data is not None:
                device.add_microsoft_defender_data(data)

    @staticmethod
    def __get_Lenovo_warranties(intune_devices):
        if len(intune_devices) == 0:
            return

        lenovo_intune_devices_by_serial_number_dictionary = dict()

        for device in intune_devices:
            # quick access for each device via its serial number, if it is a Lenovo device
            if device.manufacturer == "LENOVO":
                lenovo_intune_devices_by_serial_number_dictionary[device.serialNumber] = device

        if len(lenovo_intune_devices_by_serial_number_dictionary.keys()) == 0:
            return

        print(f"Searching for Lenovo warranties for the following devices: {lenovo_intune_devices_by_serial_number_dictionary.keys()}")

        # generate the list of serial numbers as "Serial=...&Serial=..."
        params = "Serial=" + "&Serial=".join(lenovo_intune_devices_by_serial_number_dictionary.keys())
        # fetch Lenovo warranties and stuff
        warranties = LenovoAPI.get_lenovo_warranties(params)

        # some fallback values - None should never be returned
        if warranties is None:
            warranties = []
        # this is for cases where only one item is returned, not a list of <more> items
        elif isinstance(warranties, dict):
            warranties = [warranties]
        # trigger an error if there is some unexpected behaviour
        elif not isinstance(warranties, list):
            raise TypeError(f"Unexpected warranties type: {type(warranties)}")

        # attach the warranties
        for warranty in warranties:
            serial_number = warranty.get('Serial')
            intune_device = lenovo_intune_devices_by_serial_number_dictionary[serial_number]

            error_message = warranty.get('ErrorMessage')
            if error_message is not None and error_message != "":
                print(f"Device with TOPdesk asset ID: {intune_device.topdesk_asset_id} and serial number: {serial_number} cannot be found in Lenovo warranty database: {error_message}!")
                continue

            intune_device.add_warranty(warranty)

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
        archived = TOPdesk.__get_topdesk_assets_archived_field_only(failed_to_delete_assets)

        failed_set = set(failed_to_delete_assets)
        archived_set = set(archived)

        # Debug: IDs returned as archived that were NOT in failed
        extra = archived_set - failed_set
        if extra:
            print("WARNING: archived returned IDs not in failed (filter ignored?):", list(extra)[:10])

        # Keep only those that are NOT archived
        failed_to_delete_assets[:] = [x for x in failed_to_delete_assets if x not in archived_set]

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
from devices.TOPdeskAsset import TOPdeskAsset
from platforms.TOPdesk import TOPdesk
from system.Settings import Settings

class GraphDeviceProcessor:
    API = None
    SOURCE = None
    INITIAL_URL = None
    FETCH_ALL_FLAG = None
    PAGE_LIMIT_SETTING = "NUMBER_OF_DEVICES_PAGES_ALLOWED_FOR_FETCHING"
    DEVICE_ID_FIELD_FOR_LOGGING = "id"

    @classmethod
    def process_devices(cls):
        cls.API.get_access_token()

        print(f"Fetching {cls.SOURCE.name} Devices")
        next_page = cls.INITIAL_URL

        topdesk_assets_that_must_not_be_deleted = []
        page_counter = 1

        while next_page:
            current_page_devices, next_page = cls.API.get_devices_from_page(next_page)

            print("Page:", page_counter)
            if not getattr(Settings, cls.FETCH_ALL_FLAG):
                if getattr(Settings, cls.PAGE_LIMIT_SETTING) == page_counter:
                    next_page = None
            page_counter += 1

            for device in current_page_devices:
                _, idx = TOPdeskAsset.generate_topdesk_asset_data(
                    source=cls.SOURCE,
                    data=device
                )
                topdesk_assets_that_must_not_be_deleted.append(idx)

            cls.enrich_devices(current_page_devices)

            print(
                f"Found the following {len(current_page_devices)} devices: "
                f"{[device.get(cls.DEVICE_ID_FIELD_FOR_LOGGING) for device in current_page_devices]}"
            )
            TOPdesk.create_topdesk_assets(current_page_devices, source_type=cls.SOURCE)

            print(
                f"Check the following {len(current_page_devices)} devices for any updates: "
                f"{[device.get(cls.DEVICE_ID_FIELD_FOR_LOGGING) for device in current_page_devices]}"
            )
            TOPdesk.update_topdesk_assets(current_page_devices, source_type=cls.SOURCE)

        return topdesk_assets_that_must_not_be_deleted

    @classmethod
    def enrich_devices(cls, current_page_devices):
        pass
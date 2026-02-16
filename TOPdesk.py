from ApiService import ApiService

class TOPdesk:

    @staticmethod
    def get_topdesk_assets():
        topdesk_assets = {}

        page_start = 0
        page_size = 1000
        while True:
            current_page_assets = ApiService.get_topdesk_assets_by_templates(page_start=page_start, page_size=page_size).get("dataSet")
            for asset in current_page_assets:
                topdesk_assets[asset.get("text")] = asset.get("id")

            if len(current_page_assets) == 0:
                break

            page_start += page_size

        return topdesk_assets

    @staticmethod
    def remove_device_assets_except(exceptions):
        topdesk_assets = TOPdesk.get_topdesk_assets()
        for asset in exceptions:
            if asset in topdesk_assets.keys():
                topdesk_assets.pop(asset)
        topdesk_assets = list(topdesk_assets.values())

        page_start = 0
        page_size = 100
        while True:
            if len(topdesk_assets[page_start:page_start + page_size]) == 0:
                break

            failed = ApiService.delete_assets(topdesk_assets[page_start:page_start + page_size])
            page_start += page_size

            # archive the failed ones
            for asset in failed:
                ApiService.archive_asset(asset)
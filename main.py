from system.Config import Config
from platforms.TOPdesk import TOPdesk
from system.Settings import Settings
from platforms.Intune import Intune
from platforms.Azure import Azure

#TODO:
# - move microsoft defender and lenovo to their own classes
# - hunt and fix lenovo serials not returning
###########################################################

# load config - contains ids and credentials for using various APIs
Config.load()
topdesk_assets_that_must_not_be_deleted = []

# fetch the Microsoft Defender devices at the start, as it sends all devices, no pagination involved
if Settings.FETCH_MICROSOFT_DEFENDER_DEVICES:
    TOPdesk.get_Microsoft_Defender_devices()

# proces the Azure devices
if Settings.FETCH_AZURE_DEVICES:
    processed_devices = Azure.process_devices()
    topdesk_assets_that_must_not_be_deleted.extend(processed_devices)

# proces the Intune devices
if Settings.FETCH_INTUNE_DEVICES:
    processed_devices = Intune.process_devices()
    topdesk_assets_that_must_not_be_deleted.extend(processed_devices)

# delete assets in TOPdesk that are not in Intune anymore
if Settings.DELETE_OUTDATED_TOPDESK_ASSETS:
    TOPdesk.remove_device_assets_except(topdesk_assets_that_must_not_be_deleted)

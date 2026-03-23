from system.Config import Config
from platforms.TOPdesk import TOPdesk
from system.Settings import Settings
from platforms.Intune import Intune
from platforms.Azure import Azure

# TODO #################################################################################################################
# TODO 2. Import Azure Entra ID devices ################################################################################
# TODO #################################################################################################################

# load config - contains ids and credentials for using various APIs
Config.load()

# fetch the Microsoft Defender devices at the start, as it sends all devices, no pagination involved
print("Fetching Microsoft Defender Devices")
TOPdesk.get_Microsoft_Defender_devices()

# proces the Intune devices
topdesk_assets_that_must_not_be_deleted = Intune.process_devices()

# proces the Azure devices
Azure.process_devices()

# delete assets in TOPdesk that are not in Intune anymore
if Settings.DELETE_OUTDATED_TOPDESK_ASSETS:
    TOPdesk.remove_device_assets_except(topdesk_assets_that_must_not_be_deleted)

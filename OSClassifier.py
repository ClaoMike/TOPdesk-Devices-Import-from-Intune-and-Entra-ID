from OSType import OSType
from Config import Config

class OSClassifier:
    __computer_os = {
        'Windows',
        'MacMDM',
        'macOS',
        'MacOS'
    }

    __mobile_os = {
        'Android',
        'iOS',
        'AndroidEnterprise',
    }

    @staticmethod
    def get_device_type(os: str):
        if os in OSClassifier.__computer_os:
            return OSType.COMPUTER
        elif os in OSClassifier.__mobile_os:
            return OSType.MOBILE
        else:
            return OSType.DEVICE

    @staticmethod
    def get_device_template(type: OSType):
        if type is OSType.COMPUTER:
            return Config.topdesk_computer_category_id
        elif type is OSType.MOBILE:
            return Config.topdesk_mobile_category_id
        else:
            return Config.topdesk_device_category_id
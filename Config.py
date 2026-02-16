from dotenv import load_dotenv
import os

class Config:
    tenant_id = None
    client_id = None
    client_secret = None

    topdesk_username = None
    topdesk_password = None

    topdesk_computer_category_id = None
    topdesk_mobile_category_id = None
    topdesk_device_category_id = None

    lenovo_client_id = None

    @staticmethod
    def load():
        load_dotenv(override=True)

        Config.tenant_id = os.getenv("TENANT_ID")
        Config.client_id = os.getenv("CLIENT_ID")
        Config.client_secret = os.getenv("CLIENT_SECRET")

        Config.topdesk_username = os.getenv("TOPDESK_USERNAME")
        Config.topdesk_password = os.getenv("TOPDESK_PASSWORD")

        Config.topdesk_computer_category_id = os.getenv("TOPDESK_COMPUTER_CATEGORY_ID")
        Config.topdesk_mobile_category_id = os.getenv("TOPDESK_MOBILE_CATEGORY_ID")
        Config.topdesk_device_category_id = os.getenv("TOPDESK_DEVICE_CATEGORY_ID")

        Config.lenovo_client_id = os.getenv("LENOVO_CLIENT_ID")
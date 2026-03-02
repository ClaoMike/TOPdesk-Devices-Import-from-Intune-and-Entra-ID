from system import automationassets

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
        cred = automationassets.get_automation_credential("CREDENTIAL_TOPDESK_API")
        Config.topdesk_username = cred["username"]
        Config.topdesk_password = cred["password"]

        Config.topdesk_computer_category_id =   automationassets.get_automation_variable("TOPDESK_COMPUTER_CATEGORY_ID")
        Config.topdesk_mobile_category_id =     automationassets.get_automation_variable("TOPDESK_MOBILE_CATEGORY_ID")
        Config.topdesk_device_category_id =     automationassets.get_automation_variable("TOPDESK_DEVICE_CATEGORY_ID")

        Config.tenant_id =                      automationassets.get_automation_variable("INTUNE_TENANT_ID")
        Config.client_id =                      automationassets.get_automation_variable("INTUNE_CLIENT_ID")
        Config.client_secret =                  automationassets.get_automation_variable("INTUNE_CLIENT_SECRET")

        Config.lenovo_client_id =               automationassets.get_automation_variable("LENOVO_CLIENT_ID")
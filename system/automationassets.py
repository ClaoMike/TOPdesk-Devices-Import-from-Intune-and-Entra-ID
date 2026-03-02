from dotenv import load_dotenv
import os

def get_automation_variable(key: str) -> str:
    load_dotenv(override=True)
    return os.getenv(key)

def set_automation_variable(_key: str, _value: str):
    pass

def get_automation_credential(key: str) -> dict[str, str]:
    if key == 'CREDENTIAL_TOPDESK_API':
        cred = {'username': get_automation_variable('TOPDESK_USERNAME'),
                'password': get_automation_variable('TOPDESK_PASSWORD')}

        return cred
    return {}

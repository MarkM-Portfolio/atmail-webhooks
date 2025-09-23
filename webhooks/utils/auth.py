from .helpers import logger, res_body
import os, boto3, chargebee, base64, json


def get_secrets():
    session = boto3.Session()

    try:
        cb_secrets = session.client('secretsmanager', region_name='ap-southeast-2').get_secret_value(SecretId='chargebee-secrets')
    except (Exception) as e:
        return res_body(status_code=403, msg=f'Unauthorized Access! - { str(e) }', api_src='chargebee')
    
    cb_secrets = json.loads(cb_secrets['SecretString'])

    secrets = {
        'msgco': {
            'api_key': cb_secrets.get("MSGCO_API_KEY"),
            'wh_username': cb_secrets.get('MSGCO_WEBHOOK_USERNAME'),
            'wh_password': cb_secrets.get('MSGCO_WEBHOOK_PASSWORD')
        },
        'tasman': {
            'api_key': cb_secrets.get("TASMAN_API_KEY"),
            'wh_username': cb_secrets.get('TASMAN_WEBHOOK_USERNAME'),
            'wh_password': cb_secrets.get('TASMAN_WEBHOOK_PASSWORD')
        },
        'mailserver': {
            'api_url': cb_secrets.get('MAILSERVER_URL').replace('[platform]', 'pc5'),
            'username': cb_secrets.get('MAILSERVER_USERNAME'),
            'password': cb_secrets.get('MAILSERVER_PASSWORD')
        }
    }

    return secrets

def load_secrets(req, cb_instance):
    cb_secrets = req.app.state.secrets.get(cb_instance.removesuffix('-test'))
    ms_secrets = req.app.state.secrets.get('mailserver')

    secrets = {}
    secrets.update(cb_secrets)
    secrets.update(ms_secrets)

    logger.debug(f'Secrets: { secrets }')

    chargebee.configure(secrets.get('api_key'), cb_instance)

    return secrets

def webhook_authorization(secrets, authorization, user_agent):
    logger.debug(f"================= HTTP REQUEST HEADERS =================\n\t>> Authorization : { authorization }\n\t>> User-Agent : { user_agent }")

    credentials = f"{ secrets.get('wh_username') }:{ secrets.get('wh_password') }"
    encoded_creds = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

    if f"Basic { encoded_creds }" != authorization:
        return res_body(403, "Authentication Failed!") if os.environ.get('TEST_MODE') != 'true' else None
    
    if "ChargeBee" not in user_agent:
        return res_body(403, f"Invalid User Agent: { user_agent }") if os.environ.get('TEST_MODE') != 'true' else None
    
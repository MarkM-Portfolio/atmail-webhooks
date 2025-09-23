from fastapi.testclient import TestClient
from unittest.mock import patch
from webhooks.main import app
from webhooks.utils.auth import get_secrets
import pytest


client = TestClient(app)

@pytest.fixture
def mock_secrets():
    return {
        "msgco": get_secrets().get('msgco'),
        "tasman": get_secrets().get('tasman'),
        "mailserver": get_secrets().get('mailserver')
    }

@pytest.fixture
def mock_headers():
    return {
        "Authorization": "Basic test_token",
        "User-Agent": "ChargeBee"
    }

@pytest.fixture
def mock_cb_instance():
    return "tasman-test"

@pytest.fixture
def mock_customer_payload():
    return { 
        "customer": {
            "id": "169vzoUZw6qNv6vn",
            "email": "custom01@the-bryants.org"
        }
    }

@pytest.fixture
def mock_subscription_payload():
    return { 
        "subscription": {
            "id": "16CRgJUfnWgue1sf",
            "customer_id": "6oqNhUfNzph5iXb",
            "status": "active",
            "object": "subscription",
            "subscription_items": [{
                "item_price_id": "email-tasman-standard-v1-NZD-Monthly",
                "item_type": "plan",
                "quantity": 1,
                "unit_price": 995,
                "amount": 995,
                "free_quantity": 0,
                "object": "subscription_item"
            }],
        },
        "customer": {
            "id": "6oqNhUfNzph5iXb",
            "email": "cb-test04@tasman-test.atmailcloud.com"
        }
    }

@pytest.fixture
def mock_payment_source_payload():
    return { 
        "customer": {
            "id": "169vzoUZw6qNv6vn",
            "email": "custom01@the-bryants.org",
            "billing_address": {
                "first_name": "Matt",
                "last_name": "Bryant",
                "email": "matt@the-bryants.org",
                "company": "atmail",
                "phone": "+610431496663",
                "line1": "6 Gillespie Street",
                "city": "Sippy Downs",
                "state": "Qld",
                "country": "AU",
                "zip": "4556",
                "validation_status": "not_validated",
                "object": "billing_address"
            },
            "payment_method": {
                "object": "payment_method",
                "type": "card",
                "reference_id": "tok_169vvqUbipzVGQp",
                "gateway": "chargebee",
                "gateway_account_id": "gw_AzZj4mUVTtGxy115",
                "status": "valid"
            },
            "card_status": "valid",
            "object": "customer"
        }
    }

@pytest.fixture
def mock_payment_payload():
    return { 
        "transaction": {
            "id": "txn_16BTbEUbiqpQEWf9",
            "customer_id": "169vzoUZw6qNv6vn",
            "subscription_id": "Azq8iyUbimk0ME4",
            "object": "transaction"
        },
        "invoice": {
            "id": "2",
            "customer_id": "169vzoUZw6qNv6vn",
            "subscription_id": "Azq8iyUbimk0ME4",
            "object": "invoice"
        },
        "customer": {
            "id": "169vzoUZw6qNv6vn",
            "email": "custom01@the-bryants.org"
        },
        "subscription": {
            "id": "Azq8iyUbimk0ME4",
            "customer_id": "169vzoUZw6qNv6vn",
            "status": "active",
            "object": "subscription"
        }
    }

@pytest.fixture
def mock_invoice_payload():
    return { 
        "invoice": {
            "id": "2",
            "customer_id": "169vzoUZw6qNv6vn",
            "subscription_id": "Azq8iyUbimk0ME4",
            "status": "in_progress",
            "object": "invoice"
        }
    }

@pytest.mark.parametrize("event_type, content, mock_handler", [
    ("customer_created", "mock_customer_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("customer_changed", "mock_customer_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("subscription_created", "mock_subscription_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("subscription_created_with_backdating", "mock_subscription_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("subscription_changed", "mock_subscription_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("subscription_started", "mock_subscription_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("subscription_cancelled", "mock_subscription_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("subscription_reactivated", "mock_subscription_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("subscription_paused", "mock_subscription_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("subscription_resumed", "mock_subscription_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("payment_source_added", "mock_payment_source_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("payment_succeeded", "mock_payment_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("payment_initiated", "mock_payment_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("payment_failed", "mock_payment_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook"),
    ("invoice_updated", "mock_invoice_payload", "webhooks.chargebee.v2.services.mail_service.management.chargebee_webhook")
])

def test_chargebee_webhook(mock_secrets, mock_cb_instance, mock_headers, request, event_type, content, mock_handler):
    print(f'\t>> Event Type : { event_type }')

    app.state.secrets = mock_secrets

    mock_payload = {
        "event_type": event_type,
        "webhook_status": "not_configured",
        "content": request.getfixturevalue(content)
    }

    with patch(mock_handler, return_value={"status_code": 200, "msg": "", "data": {}, "object": {}, "api_src": ""}) as mock_event_handler:
        response = client.post(f"/webhooks/chargebee/v2/mail-service/management/?cb_instance={ mock_cb_instance }", json=mock_payload, headers=mock_headers)

        assert response.status_code == 200

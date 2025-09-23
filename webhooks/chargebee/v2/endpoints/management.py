from fastapi import APIRouter, Request, Header, Query
from webhooks.models.chargebee import ChargebeeWebhookPayload, Payment, Subscription, Customer, Transaction, Invoice, PaymentSource, Card
from webhooks.models.response import ResponseBody
from webhooks.utils.auth import load_secrets, webhook_authorization
from webhooks.utils.helpers import logger, mailserver_api, res_body, timer
from typing import Dict, Union, Annotated
import os, chargebee


router = APIRouter()


@router.post("/")
async def chargebee_webhook(
    req: Request,
    payload: ChargebeeWebhookPayload,
    authorization: Annotated[Union[str, None], Header()]=None,
    user_agent: Annotated[Union[str, None], Header()]=None,
    cb_instance: str=Query(None, alias="cb-instance")
):
    event_time_start = timer(event=payload.event_type, timer='start')
    cb_instance = cb_instance if os.environ.get('TEST_MODE') != 'true' else req.query_params.get("cb_instance")
    secrets = load_secrets(req, cb_instance)
    webhook_authorization(secrets, authorization, user_agent)
    
    logger.info(f"Received Chargebe Webhook\n\t>> Chargebee Instance :\t{ cb_instance }\n\t>> Event Type :\t{ payload.event_type.title().replace('_', ' ') }\n\t>> Start Time :\t{ event_time_start }")
    logger.debug(f"Received Chargebee Webhook Payload Content\n\t{ payload.content }")

    if payload.event_type == 'customer_created':
        response = handle_customer_created(secrets, cb_instance, payload)
    elif payload.event_type == 'customer_changed':
        response = handle_customer_changed(secrets, cb_instance, payload)
    elif payload.event_type == 'subscription_created':
        response = handle_subscription_created(secrets, cb_instance, payload)
    elif payload.event_type == 'subscription_created_with_backdating':
        response = handle_subscription_created_with_backdating(secrets, cb_instance, payload)
    elif payload.event_type == 'subscription_changed':
        response = handle_subscription_changed(secrets, cb_instance, payload)
    elif payload.event_type == 'subscription_started':
        response = handle_subscription_started(secrets, cb_instance, payload)
    elif payload.event_type == 'subscription_cancelled':
        response = handle_subscription_cancelled(secrets, cb_instance, payload)
    elif payload.event_type == 'subscription_reactivated':
        response = handle_subscription_reactivated(secrets, cb_instance, payload)
    elif payload.event_type == 'subscription_paused':
        response = handle_subscription_paused(secrets, cb_instance, payload)
    elif payload.event_type == 'subscription_resumed':
        response = handle_subscription_resumed(secrets, cb_instance, payload)
    elif payload.event_type == 'payment_source_added':
        response = handle_payment_source_added(secrets, cb_instance, payload)
    elif payload.event_type == 'payment_succeeded':
        response = handle_payment_succeeded(secrets, cb_instance, payload)
    elif payload.event_type == 'payment_initiated':
        response = handle_payment_initiated(secrets, cb_instance, payload)
    elif payload.event_type == 'payment_failed':
        response = handle_payment_failed(secrets, cb_instance, payload)
    elif payload.event_type == 'invoice_updated':
        response = handle_invoice_updated(secrets, cb_instance, payload)
    else:
        return res_body(status_code=400, msg='Unhandled Event Type', data=f' { payload.event_type.title().replace('_', ' ') }', api_src='chargebee')
    
    return res_body(response.status_code, response.msg, response.data, response.object, response.api_src)

def handle_customer_created(secrets, cb_instance, payload: ChargebeeWebhookPayload):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    customer = Customer(**payload.content.get('customer'))

    logger.debug(f"Customer | cf_has_selected_a_paid_plan: { customer.cf_has_selected_a_paid_plan } { type(customer.cf_has_selected_a_paid_plan) } ")
    logger.debug(f"Customer | cf_already_paying_with_provider: { customer.cf_already_paying_with_provider } { type(customer.cf_already_paying_with_provider) } ")
    
    validation(payload.event_type, payload.content)

    if cb_instance.__contains__('tasman'):
        status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'billingCode': customer.id })
        result = { 'status_code': status_code, 'msg': f'{ action.capitalize() } Success ! { data }', 'data': payload.content, 'object': update_ms_account, 'api_src': 'mailserver' }
        response = ResponseBody(**result)

    if cb_instance.__contains__('msgco'):
        if not cb_customer_marked_as_already_selected_paid_plan(customer):
            try:
                result = chargebee.Customer.update(customer.id, { 'locale': 'en-AU', 'cf_has_selected_a_paid_plan': 'False' })
            except (Exception) as e:
                return res_body(status_code=500, msg=str(e), api_src='chargebee')
        
            logger.info(f"Update Success: <cf_has_selected_a_paid_plan>: { result }")
        
        if not cb_customer_already_paying_with_provider(customer):
            try:
                result = chargebee.Customer.update(customer.id, { 'locale': 'en-AU', 'cf_already_paying_with_provider': 'False' })
            except (Exception) as e:
                return res_body(status_code=500, msg=str(e), api_src='chargebee')
        
            logger.info(f"Update Success: <cf_already_paying_with_provider>: { result }")

            payload.event_type = "customer_changed"

            response = handle_customer_changed(secrets, cb_instance, payload) # fallthrough

    return response

def handle_customer_changed(secrets, cb_instance, payload: ChargebeeWebhookPayload):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    customer = Customer(**payload.content.get('customer'))

    validation(payload.event_type, payload.content)

    if cb_instance.__contains__('tasman'):
        status_code, action, data, get_ms_account = mailserver_api(secrets, 'GET', 'view', customer, 'account_status')
        logger.debug(f"Email: { customer.email } | Username: { get_ms_account.username }")
        logger.debug(f"Customer ID: { customer.id } | Billing Code: { get_ms_account.billingCode }")
        if get_ms_account.billingCode != customer.id:
            logger.debug(f"Billing Code (change event): Customer ID: { customer.id } | Billing Code: { get_ms_account.billingCode }")
            status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'billingCode': customer.id })
            result = { 'status_code': status_code, 'msg': f'{ action.capitalize() } Success ! { data }', 'data': payload.content, 'object': update_ms_account, 'api_src': 'mailserver' }
        if get_ms_account.username != customer.email:
            logger.debug(f"Customer Email (change event): Email: { customer.email } | Username: { get_ms_account.username }")
            status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', get_ms_account.billingCode, { 'billingCode': '' })
            result = { 'status_code': status_code, 'msg': f'{ action.capitalize() } Success ! { data }', 'data': payload.content, 'object': update_ms_account, 'api_src': 'mailserver' }

    if cb_instance.__contains__('msgco'):
        if customer.email.lower().endswith("@themessaging.co") or customer.email.lower().endswith("@team.atmail.com"):
            result = { 'status_code': 201, 'msg': 'Customer Create Success! | User', 'data': f"{ customer.email }", 'api_src': 'chargebee' }
        else:
            status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'billingCode': customer.id })
            msg = f"{ action.capitalize() }d { ', '.join(f"<{ k }> { update_ms_account.model_dump().get(k, '') }" for k in data.keys()) } | User: { update_ms_account.username }"
            result = { 'status_code': status_code, 'msg': f"Customer Create Success! | User: { customer.email } and { msg }", 'data': str(data), 'object': update_ms_account, 'api_src': 'mailserver' }

    try:
        result
    except (UnboundLocalError):
        result = { 'status_code': 200, 'msg': 'No action required', 'data': payload.content, 'api_src': 'chargebee' }
    finally:
        response = ResponseBody(**result)

    return response

def handle_subscription_created(secrets, cb_instance, payload: ChargebeeWebhookPayload):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    customer = Customer(**payload.content.get('customer'))
    subscription = Subscription(**payload.content.get('subscription'))

    validation(payload.event_type, payload.content)

    if cb_instance.__contains__('tasman'):
        if not cb_is_email_plan(cb_instance, customer, subscription):
            logger.debug(f'Subscription Status: { subscription.status }')
            result = { 'status_code': 200, 'msg': 'Ignored Event - has non-email subscription', 'data': payload.content, 'api_src': 'chargebee' }
        else:
            if cb_is_active_subscription(subscription):
                result = modify_cos_profile(secrets, cb_instance, customer, subscription, payload)
                logger.debug(f'Response Code Modify COS Profile: { result.get('status_code') }')
            else:
                result = { 'status_code': 200, 'msg': f'Ignored Event - myAccount `{ customer.email }` responsible for setting up', 'data': payload.content, 'api_src': 'chargebee' }

    if cb_instance.__contains__('msgco'):
        if cb_is_paid_plan(customer, subscription) and not cb_customer_marked_as_already_selected_paid_plan(customer):
            try:
                result = chargebee.Customer.update(customer.id, { 'locale': 'en-AU', 'cf_has_selected_a_paid_plan': 'True' })
            except (Exception) as e:
                return res_body(status_code=500, msg=str(e), api_src='chargebee')
            
            logger.info(f"Update Success: { result }")
        else:
            logger.info(f"Not Applicable: { customer.email }")

        is_owing, amount_owed = cb_active_subscriptions_fully_paid(customer)

        if is_owing or amount_owed < 50:
            status_code, action, data, get_ms_account = mailserver_api(secrets, 'GET', 'view', customer, 'account_status')
            if get_ms_account.account_status != 'active':
                status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'account_status': 'active' }) # set active if not active
                msg = f"{ action.capitalize() }d { ', '.join(f"<{ k }> { get_ms_account.model_dump().get(k, '') } => { update_ms_account.model_dump().get(k, '') }" for k in data.keys()) } | User: { update_ms_account.username }"
            else:
                msg = f"Account: { get_ms_account.username } <{ data }> is already '{ get_ms_account.account_status }'. Skipping update"

            result = { 'status_code': status_code, 'msg': msg, 'data': str(data), 'object': update_ms_account if get_ms_account.account_status != 'active' else get_ms_account, 'api_src': 'mailserver' }
        else:
            return res_body(403, f"Customer { customer.email } still owing { amount_owed }. Don't activate")
        
    try:
        result
    except (UnboundLocalError):
        result = { 'status_code': 200, 'msg': 'No action required', 'data': payload.content, 'api_src': 'chargebee' }
    finally:
        response = ResponseBody(**result)

    return response

def handle_subscription_created_with_backdating(secrets, cb_instance, payload: ChargebeeWebhookPayload):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    customer = Customer(**payload.content.get('customer'))
    subscription = Subscription(**payload.content.get('subscription'))
    
    validation(payload.event_type, payload.content)

    if cb_instance.__contains__('tasman'):
        if not cb_is_email_plan(cb_instance, customer, subscription):
            logger.debug(f'Subscription Status: { subscription.status }')
            result = { 'status_code': 200, 'msg': 'Ignored Event - has non-email subscription', 'data': payload.content, 'api_src': 'chargebee' }
        else:
            if cb_is_active_subscription(subscription):
                result = modify_cos_profile(secrets, cb_instance, customer, subscription, payload)
                logger.debug(f'Response Code Modify COS Profile: { result.get('status_code') }')
            else:
                result = { 'status_code': 200, 'msg': f'Ignored Event - myAccount `{ customer.email }` responsible for setting up', 'data': payload.content, 'api_src': 'chargebee' }

    if cb_instance.__contains__('msgco'):
        cancel_active_sponsored_subs_for_customer_other_than(payload.content)

        if cb_is_paid_plan(customer, subscription):
            result = modify_cos_profile(secrets, cb_instance, customer, subscription, payload)
            logger.debug(f'Response Code Modify COS Profile: { result.get('status_code') }')
        else:
            result = { 'status_code': 201, 'msg': f'Not a paid plan. Subscription created successfully. | User: { customer.email }', 'data': f'Subscription: { subscription }', 'api_src': 'chargebee' }

    try:
        result
    except (UnboundLocalError):
        result = { 'status_code': 200, 'msg': 'No action required', 'data': payload.content, 'api_src': 'chargebee' }
    finally:
        response = ResponseBody(**result)

    return response

def handle_subscription_changed(secrets, cb_instance, payload: ChargebeeWebhookPayload):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    customer = Customer(**payload.content.get('customer'))
    subscription = Subscription(**payload.content.get('subscription'))

    validation(payload.event_type, payload.content)

    if cb_instance.__contains__('tasman'):
        if not cb_is_email_plan(cb_instance, customer, subscription):
            logger.debug(f'Subscription Status: { subscription.status }')
            result = { 'status_code': 200, 'msg': 'Ignored Event', 'data': payload.content, 'api_src': 'chargebee' }
        else:
            active_subs = cb_all_subscriptions(customer, { 'status[is]': 'active' })
            sub_status_set = [ 'rstrBilling', 'rstrFrozen', 'disabled', 'deleted' ] if not cb_is_active_subscription(subscription) else [ 'active' ] if len(active_subs) or cb_is_active_subscription(subscription) else []
            logger.debug(f'Active Subs: { active_subs }, length: { len(active_subs) } | Account Status: { sub_status_set }')

            result = modify_cos_profile(secrets, cb_instance, customer, subscription, payload) if cb_is_active_subscription(subscription) else { 'status_code': 200, 'msg': f'Ignored Event', 'data': f' { payload.event_type.title().replace('_', ' ') } - dont care if changes not to active subscription | User: { customer.email }', 'api_src': 'chargebee' }
            logger.debug(f'Response Code Modify COS Profile: { result.get('status_code') }') if cb_is_active_subscription(subscription) else None

            status_code, action, data, get_ms_account = mailserver_api(secrets, 'GET', 'view', customer, 'account_status')
            logger.debug(f'Mail Server Account Status: { get_ms_account.account_status }')

            if get_ms_account.account_status not in sub_status_set:
                status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'account_status': sub_status_set[0] })
                result = { 'status_code': status_code, 'msg': f'{ action.capitalize() } Success ! { data }', 'data': payload.content, 'object': update_ms_account, 'api_src': 'mailserver' }

    if cb_instance.__contains__('msgco'):
        if cb_is_paid_plan(customer, subscription) and subscription.status != 'future':
            result = modify_cos_profile(secrets, cb_instance, customer, subscription, payload)
            logger.debug(f'Response Code Modify COS Profile: { result.get('status_code') }')

            is_owing, amount_owed = cb_active_subscriptions_fully_paid(customer)
            logger.debug(f"Is Owing: { is_owing } | Amount Owing: { amount_owed }")

            status_code, action, data, get_ms_account = mailserver_api(secrets, 'GET', 'view', customer, 'account_status')
            logger.debug(f'Mail Server Account Status: { get_ms_account.account_status }')

            if is_owing or amount_owed < 50:
                if get_ms_account.account_status != 'active':
                    status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'account_status': 'active' }) # set active if not active
                    msg = f"{ action.capitalize() }d { ', '.join(f"<{ k }> { get_ms_account.model_dump().get(k, '') } => { update_ms_account.model_dump().get(k, '') }" for k in data.keys()) } | User: { update_ms_account.username }"
                else:
                    msg = f"Account: { get_ms_account.username } <{ data }> is already '{ get_ms_account.account_status }'. Skipping update"
            else:
                if get_ms_account.account_status == 'active':
                    status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'account_status': 'rstrBilling' }) # set restricted billing if active
                    msg = f"{ action.capitalize() }d { ', '.join(f"<{ k }> { get_ms_account.model_dump().get(k, '') } => { update_ms_account.model_dump().get(k, '') }" for k in data.keys()) } | User: { update_ms_account.username }"
                else:
                    msg = f"Account: { get_ms_account.username } <{ data }> is already '{ get_ms_account.account_status }'. Skipping update"

            result = { 'status_code': status_code, 'msg': msg, 'data': str(data), 'object': update_ms_account if get_ms_account.account_status != 'active' else get_ms_account, 'api_src': 'mailserver' }
            
    try:
        result
    except (UnboundLocalError):
        msg = f'Ignored Event - dont care if changes not to active subscription' if cb_instance.__contains__('tasman') else 'No action required - not a paid plan' if cb_instance.__contains__('msgco') else None
        result = { 'status_code': 200, 'msg': msg, 'data': data, 'data': payload.content, 'api_src': 'chargebee' }
    finally:
        response = ResponseBody(**result)

    return response

def handle_subscription_started(secrets, cb_instance, payload: ChargebeeWebhookPayload):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    customer = Customer(**payload.content.get('customer'))
    subscription = Subscription(**payload.content.get('subscription'))

    validation(payload.event_type, payload.content)

    if cb_instance.__contains__('tasman'):
        if not cb_is_email_plan(cb_instance, customer, subscription):
            logger.debug(f'Subscription Status: { subscription.status }')
            result = { 'status_code': 200, 'msg': 'Ignored Event', 'data': payload.content, 'api_src': 'chargebee' }
        else:
            if cb_is_active_subscription(subscription):
                result = modify_cos_profile(secrets, cb_instance, customer, subscription, payload)
                logger.debug(f'Response Code Modify COS Profile: { result.get('status_code') }')
                status_code, action, data, get_ms_account = mailserver_api(secrets, 'GET', 'view', customer, 'account_status')
                logger.debug(f'Mail Server Account Status: { get_ms_account.account_status }')
                if get_ms_account.account_status != 'active':
                    status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'account_status': 'active' })
                    result = { 'status_code': status_code, 'msg': f'{ action.capitalize() } Success ! { data }', 'data': payload.content, 'object': update_ms_account, 'api_src': 'mailserver' }
            else:
                result = { 'status_code': 200, 'msg': 'Ignored Event', 'data': payload.content, 'api_src': 'chargebee' }

        try:
            result
        except (UnboundLocalError):
            result = { 'status_code': 200, 'msg': 'No action required', 'data': payload.content, 'api_src': 'chargebee' }
        finally:
            response = ResponseBody(**result)

    if cb_instance.__contains__('msgco'):
        cancel_active_sponsored_subs_for_customer_other_than(payload.content) # check number of subscription_items here
        payload.event_type='subscription_changed'

        response = handle_subscription_changed(secrets, cb_instance, payload) # fallthrough

    return response

def handle_subscription_cancelled(secrets, cb_instance, payload: ChargebeeWebhookPayload):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    customer = Customer(**payload.content.get('customer'))
    subscription = Subscription(**payload.content.get('subscription'))

    validation(payload.event_type, payload.content)

    if cb_instance.__contains__('tasman'):
        if not cb_is_email_plan(cb_instance, customer, subscription):
            logger.debug(f'Subscription Status: { subscription.status }')
            result = { 'status_code': 200, 'msg': 'Ignored Event', 'data': payload.content, 'api_src': 'chargebee' }
        else:
            active_subs = cb_all_subscriptions(customer, { 'status[is]': 'active' })
            logger.debug(f'Active Subs: { active_subs }, length: { len(active_subs) }')
            sub_status_set = [ 'rstrBilling', 'rstrFrozen' ] if cb_plan_family(cb_instance, customer, subscription) == 'email-tasman' else [ 'rstrBilling' ]

            if len(active_subs):
                result = { 'status_code': 200, 'msg': 'Ignored Event - has active subscription', 'data': payload.content, 'api_src': 'chargebee' }
            else:
                result = modify_cos_profile(secrets, cb_instance, customer, subscription, payload)
                logger.debug(f'Response Code Modify COS Profile: { result.get('status_code') }')
                status_code, action, data, get_ms_account = mailserver_api(secrets, 'GET', 'view', customer, 'account_status')
                logger.debug(f'Mail Server Account Status: { get_ms_account.account_status }')
                if get_ms_account.account_status not in sub_status_set:
                    status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'account_status': sub_status_set[0] })
                    result = { 'status_code': status_code, 'msg': f'{ action.capitalize() } Success ! { data }', 'data': payload.content, 'object': update_ms_account, 'api_src': 'mailserver' }

    if cb_instance.__contains__('msgco'):
        for plan in cb_all_subscriptions(customer):
            if cb_is_paid_plan(plan):
                if plan.status in [ 'active', 'future', 'non_renewing' ]:
                    if plan.id != subscription.id:
                        if cb_plan_check(cb_instance, plan, 'storage') > cb_plan_check(cb_instance, subscription, 'storage', cb_plan_check=cb_instance):
                            logger.debug(f"Active Subscription: { cb_plan_check(cb_instance, plan, 'storage') } > Subscription Payload: { cb_plan_check(cb_instance, subscription, 'storage') }")
                            highest_quota_subcription = plan

                        try:
                            highest_quota_subcription
                            logger.debug(f"Highest Quota Subcription: { highest_quota_subcription }")
                        except (Exception) as e:
                            return res_body(status_code=422, msg=str(e), api_src='chargebee')
                        else:
                            result = modify_cos_profile(secrets, cb_instance, customer, highest_quota_subcription)
                            logger.debug(f'Response Code Modify COS Profile: { result.get('status_code') }')
    
    try:
        result
    except (UnboundLocalError):
        result = { 'status_code': 200, 'msg': 'No action required', 'data': payload.content, 'api_src': 'chargebee' }
    finally:
        response = ResponseBody(**result)

    return response

def handle_subscription_reactivated(secrets, cb_instance, payload: ChargebeeWebhookPayload, fallthrough: str=None):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    customer = Customer(**payload.content.get('customer')) if fallthrough is None else ''
    subscription = Subscription(**payload.content.get('subscription')) if fallthrough is None else ''

    logger.debug(f"Customer ID: { customer.id } | Customer Email: { customer.email } | Subscription ID: { subscription.id }") if fallthrough is None else ''
    
    validation(payload.event_type if fallthrough is None else fallthrough, payload.content)

    if cb_instance.__contains__('tasman'):
        if not cb_is_email_plan(cb_instance, customer, subscription):
            logger.debug(f'Subscription Status: { subscription.status }')
            result = { 'status_code': 200, 'msg': 'Ignored Event', 'data': payload.content, 'api_src': 'chargebee' }
        else:
            result = modify_cos_profile(secrets, cb_instance, customer, subscription, payload)
            logger.debug(f'Response Code Modify COS Profile: { result.get('status_code') }')
            status_code, action, data, get_ms_account = mailserver_api(secrets, 'GET', 'view', customer, 'account_status')
            logger.debug(f'Mail Server Account Status: { get_ms_account.account_status }')
            if get_ms_account.account_status != 'active':
                status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'account_status': 'active' })
                result = { 'status_code': status_code, 'msg': f'{ action.capitalize() } Success ! { data }', 'data': payload.content, 'object': update_ms_account, 'api_src': 'mailserver' }

        try:
            result
        except (UnboundLocalError):
            result = { 'status_code': 200, 'msg': 'No action required', 'data': payload.content, 'api_src': 'chargebee' }
        finally:
            response = ResponseBody(**result)
        
    if cb_instance.__contains__('msgco'):
        event_source = payload.event_type
        payload.event_type = "payment_succeeded"

        response = handle_payment_succeeded(payload, cb_instance, fallthrough if fallthrough is not None else event_source) # fallthrough

    return response

def handle_subscription_paused(secrets, cb_instance, payload: ChargebeeWebhookPayload):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    customer = Customer(**payload.content.get('customer'))
    subscription = Subscription(**payload.content.get('subscription'))

    validation(payload.event_type, payload.content)

    if cb_instance.__contains__('tasman'):
        if not cb_is_email_plan(cb_instance, customer, subscription):
            logger.debug(f'Subscription Status: { subscription.status }')
            result = { 'status_code': 200, 'msg': 'Ignored Event', 'data': payload.content, 'api_src': 'chargebee' }
        else:
            status_code, action, data, get_ms_account = mailserver_api(secrets, 'GET', 'view', customer, 'account_status')
            logger.debug(f'Mail Server Account Status: { get_ms_account.account_status }')
            if get_ms_account.account_status not in [ 'rstrBilling', 'rstrFrozen' ]:
                status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'account_status': 'rstrBilling' })
                result = { 'status_code': status_code, 'msg': f'{ action.capitalize() } Success ! { data }', 'data': payload.content, 'object': update_ms_account, 'api_src': 'mailserver' }

        try:
            result
        except (UnboundLocalError):
            result = { 'status_code': 200, 'msg': 'No action required', 'data': payload.content, 'api_src': 'chargebee' }
        finally:
            response = ResponseBody(**result)

    if cb_instance.__contains__('msgco'):
        payload.event_type = "subscription_cancelled"

        response = handle_subscription_cancelled(secrets, cb_instance, payload) # fallthrough

    return response

def handle_subscription_resumed(secrets, cb_instance, payload: ChargebeeWebhookPayload, fallthrough: str=None):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    customer = Customer(**payload.content.get('customer')) if fallthrough is None else ''
    subscription = Subscription(**payload.content.get('subscription')) if fallthrough is None else ''

    validation(payload.event_type if fallthrough is None else fallthrough, payload.content)

    if cb_instance.__contains__('tasman'):
        if not cb_is_email_plan(cb_instance, customer, subscription):
            logger.debug(f'Subscription Status: { subscription.status }')
            result = { 'status_code': 200, 'msg': 'Ignored Event', 'data': payload.content, 'api_src': 'chargebee' }
        else:
            status_code, action, data, get_ms_account = mailserver_api(secrets, 'GET', 'view', customer, 'account_status')
            logger.debug(f'Mail Server Account Status: { get_ms_account.account_status }')
            if get_ms_account.account_status != 'active':
                status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'account_status': 'active' })
                result = { 'status_code': status_code, 'msg': f'{ action.capitalize() } Success ! { data }', 'data': payload.content, 'object': update_ms_account, 'api_src': 'mailserver' }

        try:
            result
        except (UnboundLocalError):
            result = { 'status_code': 200, 'msg': 'No action required', 'data': payload.content, 'api_src': 'chargebee' }
        finally:
            response = ResponseBody(**result)
        
    if cb_instance.__contains__('msgco'):
        event_source = payload.event_type if fallthrough is None else fallthrough
        payload.event_type = 'subscription_reactivated'

        response = handle_subscription_reactivated(secrets, cb_instance, payload, event_source) # fallthrough

    return response

def handle_payment_source_added(secrets, cb_instance, payload: ChargebeeWebhookPayload):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    if cb_instance.__contains__('tasman'):
        result = { 'status_code': 200, 'msg': 'Ignored Event - Not interested in payment events for tasman', 'data': payload.content, 'api_src': 'chargebee' }

    if cb_instance.__contains__('msgco'):
        payment_source = PaymentSource(**payload.content.get('customer'))
        card = Card(**payload.content.get('customer'))

        logger.debug(f"Payment Source: { payment_source }")

        validation(payload.event_type, payload.content)

        if payment_source.billing_address is None or payment_source.billing_address == '' and payment_source.payment_method.type == 'card':
            if payment_source.card_status is None or payment_source.card_status != 'valid':
                return res_body(status_code=400, msg='Invalid card content', api_src='chargebee')

            logger.debug(f"card: { card }")

            billing_address = {
                'first_name': card.first_name,
                'last_name': card.last_name,
                'line1': card.billing_addr1,
                'city': card.billing_city,
                'state': card.billing_state,
                'country': card.billing_country,
                'zip': card.billing_zip
            }

            try:
                result = chargebee.Customer.update_billing_info(payment_source.id, { 'first_name': card.first_name, 'last_name': card.last_name, 'billing_address': billing_address })
            except (Exception) as e:
                return res_body(status_code=500, msg=str(e), api_src='chargebee')
            
            result = { 'status_code': 201, 'msg': 'Customer Create Success! | User', 'data': f"{ payment_source.email }", 'api_src': 'chargebee' }

    try:
        result
    except (UnboundLocalError):
        result = { 'status_code': 200, 'msg': 'No action required', 'api_src': 'chargebee' }
    finally:
        response = ResponseBody(**result)

    return response

def handle_payment_succeeded(secrets, cb_instance, payload: ChargebeeWebhookPayload, fallthrough: str=None):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    if cb_instance.__contains__('tasman'):
        result = { 'status_code': 200, 'msg': 'Ignored Event - Not interested in payment events for tasman', 'data': payload.content, 'api_src': 'chargebee' }

    if cb_instance.__contains__('msgco'):
        logger.debug(f"Content: { payload.content }")
        logger.debug(f"Fallthrough: { fallthrough }")

        customer = Payment(**payload.content).customer if fallthrough is None else \
            Customer(**payload.content.get('customer')) if fallthrough.split('_')[0] == 'subscription' else \
            Invoice(**payload.content.get('invoice')).customer_id if fallthrough.split('_')[0] == 'invoice' else ''
        
        logger.debug(f"Data Type: { type(customer) }")

        validation(payload.event_type if fallthrough is None else fallthrough, payload.content)
        
        is_owing, amount_owed = cb_active_subscriptions_fully_paid(customer)
        logger.debug(f"Is Owing: { is_owing } | Amount Owing: { amount_owed }")
        
        status_code, action, data, get_ms_account = mailserver_api(secrets, 'GET', 'view', customer, 'account_status')
        logger.debug(f'Mail Server Account Status: { get_ms_account.account_status }')

        if is_owing or amount_owed < 50:
            if get_ms_account.account_status != 'active':
                status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'account_status': 'active' }) # set active if not active
                msg = f"{ action.capitalize() }d { ', '.join(f"<{ k }> { get_ms_account.model_dump().get(k, '') } => { update_ms_account.model_dump().get(k, '') }" for k in data.keys()) } | User: { update_ms_account.username }"
            else:
                msg = f"Account: { get_ms_account.username } <{ data }> is already '{ get_ms_account.account_status }'. Skipping update"
        else:
            if get_ms_account.account_status == 'active':
                status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'account_status': 'rstrBilling' }) # set billing restricted if active
                msg = f"{ action.capitalize() }d { ', '.join(f"<{ k }> { get_ms_account.model_dump().get(k, '') } => { update_ms_account.model_dump().get(k, '') }" for k in data.keys()) } | User: { update_ms_account.username }"
            else:
                msg = f"Account: { get_ms_account.username } <{ data }> is already '{ get_ms_account.account_status }'. Skipping update"

        result = { 'status_code': status_code, 'msg': msg, 'data': str(data), 'object': update_ms_account if get_ms_account.account_status != 'active' else get_ms_account, 'api_src': 'mailserver' }

    try:
        result
    except (UnboundLocalError):
        result = { 'status_code': 200, 'msg': 'No action required', 'api_src': 'chargebee' }
    finally:
        response = ResponseBody(**result)
    
    return response

def handle_payment_initiated(secrets, cb_instance, payload: ChargebeeWebhookPayload):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    if cb_instance.__contains__('tasman'):
        result = { 'status_code': 200, 'msg': 'Ignored Event - Not interested in payment events for tasman', 'data': payload.content, 'api_src': 'chargebee' }

    if cb_instance.__contains__('msgco'):
        payment = Payment(**payload.content)

        logger.debug(f"Payment Customer ID { payment.customer.id } { payment.customer.email }")
        logger.debug(f"Payment Subscription ID { payment.subscription.id }")
        logger.debug(f"Payment Invoice ID { payment.invoice.id }")
        logger.debug(f"Payment Transaction ID { payment.transaction.id }")

        validation(payload.event_type, payload.content)

        status_code, action, data, get_ms_account = mailserver_api(secrets, 'GET', 'view', payment.customer, 'account_status')
        logger.debug(f'Mail Server Account Status: { get_ms_account.account_status }')
        if get_ms_account.account_status != 'active':
            status_code, action, data, update_ms_account = mailserver_api(secrets, 'POST', 'update', payment.customer, { 'account_status': 'active' }) # set active if not active
            msg = f"{ action.capitalize() }d { ', '.join(f"<{ k }> { get_ms_account.model_dump().get(k, '') } => { update_ms_account.model_dump().get(k, '') }" for k in data.keys()) } | User: { update_ms_account.username }"
        else:
            msg = f"Account: { get_ms_account.username } <{ data }> is already '{ get_ms_account.account_status }'. Skipping update"

        result = { 'status_code': status_code, 'msg': msg, 'data': str(data), 'object': update_ms_account if get_ms_account.account_status != 'active' else get_ms_account, 'api_src': 'mailserver' }

    try:
        result
    except (UnboundLocalError):
        result = { 'status_code': 200, 'msg': 'No action required', 'api_src': 'chargebee' }
    finally:
        response = ResponseBody(**result)
    
    return response

def handle_payment_failed(secrets, cb_instance, payload: ChargebeeWebhookPayload):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    if cb_instance.__contains__('tasman'):
        result = { 'status_code': 200, 'msg': 'Ignored Event - Not interested in payment events for tasman', 'data': payload.content, 'api_src': 'chargebee' }
        response = ResponseBody(**result)
    
    if cb_instance.__contains__('msgco'):
        return res_body(status_code=400, msg='Unhandled Event Type', data=f' { payload.event_type.title().replace('_', ' ') }', api_src='chargebee')
    
    return response

def handle_invoice_updated(secrets, cb_instance, payload: ChargebeeWebhookPayload):
    logger.debug(f"[ EVENT ] - { payload.event_type }")

    if cb_instance.__contains__('tasman'):
        result = { 'status_code': 200, 'msg': 'Ignored Event - Not interested in payment events for tasman', 'data': payload.content, 'api_src': 'chargebee' }
        response = ResponseBody(**result)

    if cb_instance.__contains__('msgco'):
        invoice = Invoice(**payload.content.get('invoice'))

        logger.debug(f"Invoice ID { invoice.id } || Customer ID: { invoice.customer_id }")

        validation(payload.event_type, payload.content)

        try:
            transactions_in_progress = chargebee.Transaction.list({ 'customer_id[is]': invoice.customer_id, 'limit': 2, 'status[is]': 'in_progress' })
        except (Exception) as e:
            return res_body(status_code=500, msg=str(e), api_src='chargebee')    
        
        if len(transactions_in_progress) > 0:
            result = { 'status_code': 200, 'msg': f"Transactions in progress: { len(transactions_in_progress) }, not changing account status", 'api_src': 'chargebee' }
            response = ResponseBody(**result)
        else:
            logger.info(f"No payment transactions in progress: { len(transactions_in_progress) }")
            
            event_source = payload.event_type
            payload.event_type = 'subscription_resumed'

            response = handle_subscription_resumed(secrets, cb_instance, payload, event_source) # fallthrough

    return response

def cb_all_subscriptions(customer: Union[Customer, str], data: str=None):
    params = { 'customer_id[is]': customer if isinstance(customer, str) else customer.id }
    params.update(data) if data else params

    try:
        subscriptions = chargebee.Subscription.list(params=params)
    except (Exception) as e:
        return res_body(status_code=400, msg=str(e) if not data else f'No { data } in subscriptions', data=f'| User: { customer.email }', api_src='chargebee')
    
    all_subscriptions = [ Subscription(**sub._response['subscription']) for sub in subscriptions ]

    logger.debug(f"All Subscriptions: { all_subscriptions }")

    return all_subscriptions

def cb_plan_check(cb_instance: str, subscription: Subscription, params: str=None):
    storage = 0
    cos_profile = ''
    prefixes = [ 'email-' ] if cb_instance.__contains__('tasman') else [ 'plan-av', 'plan-bv', 'plan-cv', 'complimentary-plan-' ] if cb_instance.__contains__('msgco') else None
    plan_types = [ 'plan' ] if cb_instance.__contains__('tasman') else [ 'plan', 'addon', 'charge' ] if cb_instance.__contains__('msgco') else None

    for plan in subscription.subscription_items:
        if plan.item_type in plan_types:
            plan_name = plan.item_price_id.lower()
            prefix = next((prefix for prefix in prefixes if plan.item_price_id.lower().startswith(prefix)), None)

            if prefix and cb_instance.__contains__('tasman'):
                cos_profile = '-'.join(plan.item_price_id.lower().rsplit('-', 2)[:-2]) + '.group'
            if prefix and cb_instance.__contains__('msgco'):
                if prefix == 'plan-av':
                    storage = 2 * 1024 * 1024 * 1024 # 2GB
                    cos_profile = 'Kakadu-Plan-AV1'
                if prefix == 'plan-bv':
                    storage = 15 * 1024 * 1024 * 1024 # 15GB
                    cos_profile = 'Kakadu-Plan-BV1'
                if prefix == 'plan-cv':
                    storage = 100 * 1024 * 1024 * 1024 # 100GB
                    cos_profile = 'Kakadu-Plan-CV1'
                if prefix == 'complimentary-plan-':
                    storage = 100 * 1024 * 1024 * 1024 # 100GB
                    cos_profile = 'Kakadu-complimentary-plan'

    logger.debug(f"Plan Name: { plan_name } | Storage: { storage }") if params == 'storage' else logger.debug(f"Plan Name: { plan_name } | COS Profile Name: { cos_profile }") if params == 'cos_profile' \
        else logger.debug(f"Plan Name: { plan_name } | Storage: { storage } | COS Profile Name: { cos_profile }") if params is None else ''
        
    return storage if params == 'storage' else cos_profile if params == 'cos_profile' \
        else (storage, cos_profile) if params is None \
        else res_body(status_code=400, msg='Incorrect parameters for cb_plan_check function', api_src='mailserver')

def cb_plan_family(cb_instance, customer: Customer, subscription: Subscription):
    prefixes = [ 'email-' ] if cb_instance.__contains__('tasman') else [ 'plan-av', 'plan-bv', 'plan-cv', 'complimentary-plan-' ] if cb_instance.__contains__('msgco') else ''
    plan_types = [ 'plan' ] if cb_instance.__contains__('tasman') else [ 'plan', 'addon', 'charge' ] if cb_instance.__contains__('msgco') else None

    try:
        if subscription.subscription_items is None:
            raise Exception('No subscription items')
    except (Exception) as e:
        return res_body(status_code=422, msg=f"{ e } | User", data=f" { customer.email }",  api_src='chargebee')
    
    for plan in subscription.subscription_items:
        if plan.item_type in plan_types and any(plan.item_price_id.lower().startswith(prefix) for prefix in prefixes):
            plan_family = 'email-tasman-legacy' if 'legacy'.lower() in plan.item_price_id.lower() else 'email-tasman'
            logger.debug(f"Plan Name: { plan.item_price_id.lower() } | Subscription Item ID: { subscription.id } | Plan Family: { plan_family }")
                
    return plan_family

def cb_is_email_plan(cb_instance, customer: Customer, subscription: Subscription):
    is_email_plan = False
    prefixes = [ 'email-' ] if cb_instance.__contains__('tasman') else [ 'plan-av', 'plan-bv', 'plan-cv', 'complimentary-plan-' ] if cb_instance.__contains__('msgco') else ''
    plan_types = [ 'plan' ] if cb_instance.__contains__('tasman') else [ 'plan', 'addon', 'charge' ] if cb_instance.__contains__('msgco') else None

    try:
        if subscription.subscription_items is None:
            raise Exception('No subscription items')
    except (Exception) as e:
        return res_body(status_code=422, msg=f"{ e } | User", data=f" { customer.email }",  api_src='chargebee')
    
    for plan in subscription.subscription_items:
        if plan.item_type in plan_types and any(plan.item_price_id.lower().startswith(prefix) for prefix in prefixes):
            is_email_plan = True
            logger.debug(f"Plan Name: { plan.item_price_id.lower() } | Subscription Item ID: { subscription.id } | Is Email Plan: { is_email_plan }")
                
    return is_email_plan

def cb_is_paid_plan(customer: Customer, subscription: Subscription, cb_instance):
    is_paid_plan = False
    prefixes = [ 'email-' ] if cb_instance.__contains__('tasman') else [ 'plan-av', 'plan-bv', 'plan-cv', 'complimentary-plan-' ] if cb_instance.__contains__('msgco') else ''
    plan_types = [ 'plan' ] if cb_instance.__contains__('tasman') else [ 'plan', 'addon', 'charge' ] if cb_instance.__contains__('msgco') else None

    try:
        if subscription.subscription_items is None:
            raise Exception('No subscription items')
    except (Exception) as e:
        return res_body(status_code=422, msg=f"{ e } | User", data=f" { customer.email }",  api_src='chargebee')
    
    for plan in subscription.subscription_items:
        if plan.item_type in plan_types and any(plan.item_price_id.lower().startswith(prefix) for prefix in prefixes):
            # is_paid_plan = False if 'legacy'.lower() in plan.item_price_id.lower() else True
            is_paid_plan = True
            logger.debug(f"Plan Name: { plan.item_price_id.lower() } | Subscription Item ID: { subscription.id } | Is Paid Plan: { is_paid_plan }")
                
    return is_paid_plan

def cb_customer_marked_as_already_selected_paid_plan(customer: Customer):
    try:
        if not customer.cf_has_selected_a_paid_plan:
            raise Exception()
    except (Exception):
        return False

    return True

def cb_customer_already_paying_with_provider(customer: Customer):
    try:
        if not customer.cf_already_paying_with_provider:
            raise Exception()
    except (Exception):
        return False

    return True

def cb_active_subscriptions_fully_paid(customer: Union[Customer, str]):
    total_amount_due = 0

    for plan in cb_all_subscriptions(customer):
        if plan.status in [ 'active', 'future', 'non_renewing' ]:
            total_amount_due += plan.due_invoices_count
        else:
            return res_body(status_code=500, msg=f'No active subscriptions | User: { customer if isinstance(customer, str) else customer.email }', api_src='chargebee')

    if total_amount_due == 0:
        return True, total_amount_due
    
    return False, total_amount_due

def cb_is_active_subscription(subscription: Subscription):
    logger.debug(f"Subscription { subscription }")

    if subscription.status in [ 'active', 'non_renewing' ]:
        logger.debug(f"Is Active Subscription")
        return True
    else:
        logger.debug(f"Is Not Active Subscription")
        return False

def cancel_active_sponsored_subs_for_customer_other_than(content: Dict, cb_instance):
    customer = Customer(**content.get('customer'))
    subscription = Subscription(**content.get('subscription'))

    plan_types = [ 'plan' ] if cb_instance.__contains__('tasman') else [ 'plan', 'addon', 'charge' ] if cb_instance.__contains__('msgco') else None

    try:
        if subscription.subscription_items is None:
            raise Exception('No subscription items')
    except (Exception) as e:
        return res_body(status_code=422, msg=f"{ e } | User", data=f" { customer.email }",  api_src='chargebee')

    for plan in subscription.subscription_items:
        if plan.item_type in plan_types:
            new_plan_price = plan.unit_price
            logger.debug(f"New Plan | Item Price ID: { plan.item_price_id }, Unit Price: { plan.unit_price }")

    for plan in cb_all_subscriptions(customer, { 'status[is]': 'active' }):
        if plan.id != subscription.id:
            for sub_item in plan.subscription_items:
                if sub_item.item_type in plan_types:
                    logger.debug(f"Subscription Item | Item Price ID: { sub_item.item_price_id } | Unit Pirce: { sub_item.unit_price } | Item Type: { sub_item.item_type }")
                    if sub_item.item_price_id == 'email-account-AUD-Monthly' and sub_item.unit_price == 0:
                        cancel_reason = 'Duplicate Subscription'
                        if new_plan_price > 0 and sub_item.unit_price == 0:
                            cancel_reason = "Moved to a Paid Plan"
                        try:
                            chargebee.Subscription.cancel_for_items(plan.id, {
                                'end_of_term': False,
                                'credit_option_for_current_term_charges': 'None',
                                "unbilled_charges_option": 'Delete',
                                "account_receivables_handling": 'NoAction',
                                "refundable_credits_handling": 'NoAction',
                                "cancel_reason_code": cancel_reason
                            })
                        except (Exception) as e:
                            return res_body(status_code=500, msg=str(e), api_src='chargebee')
                        logger.info(f"Cancelled subscription { plan.id }: { cancel_reason }")                      
                    else:
                        logger.info(f"Subscription doesn't quality for cancellation: { plan.id }")
                else:
                    logger.info(f"Found subscription to not delete: { customer.email } | { customer.id }")

def modify_cos_profile(secrets, cb_instance, customer: Customer, subscription: Subscription, payload: ChargebeeWebhookPayload):
    logger.debug(f"Customer { customer }")
    logger.debug(f"Subscription { subscription }")
    
    _, _, _, get_ms_account = mailserver_api(secrets, 'GET', 'view', customer, 'account_status')
    storage_usage = get_ms_account.mailUsedBytes + get_ms_account.fileUsedBytes

    try:
        cos_profiles = get_ms_account.cosProfile[0].profile
    except (Exception) as e:
        return res_body(status_code=500, msg='No COS profiles returned from mailserver', api_src='mailserver')
    
    include_storage, new_cos_profile_name = cb_plan_check(cb_instance, subscription)

    try:
        new_cos_profile = next((profile for profile in cos_profiles if profile.name == new_cos_profile_name), None)
        if new_cos_profile is None:
            if new_cos_profile_name == '':
                raise Exception(f'No value for COS profile name: { new_cos_profile_name }')
            raise Exception(f'Unknown COS profile name: { new_cos_profile_name }, likely not a real { cb_instance.removesuffix('-test') } account')
    except (Exception) as e:
        return res_body(status_code=422, msg=str(e), api_src='mailserver')

    if cb_instance.__contains__('msgco'):
        logger.debug(f"Storage used: { storage_usage }, Entitlement: { include_storage }")

        if include_storage == 0:
            # This is an unhandled COS profile / plan combination
            result = { 'status_code': 200, 'msg': 'Unknown COS equivalent, saying OK - probably needs to change in the future'}
        if storage_usage >= include_storage:
            logger.info(f"Modifying COS will put account over quota. Current usage: { storage_usage } Bytes")

    current_cos_profile = next(profile for profile in cos_profiles if profile.active)
    logger.debug(f"Current COS Profile: { current_cos_profile }")

    if new_cos_profile.name == current_cos_profile.name:
        result = { 'status_code': 200, 'msg': f'Ignored Event: Current COS profile { current_cos_profile } already selected. Skipping update', 'api_src': 'mailserver'}
    else:
        status_code, action, _, update_ms_account = mailserver_api(secrets, 'POST', 'update', customer, { 'cosProfileId': new_cos_profile.id, 'disableQuotaCheck': 1 })
        result = { 'status_code': status_code, 'msg': f'{ action.capitalize() } Success ! { current_cos_profile.name } => { new_cos_profile.name }', 'data': payload.content, 'object': update_ms_account, 'api_src': 'mailserver' }

    return result

def validation(event_type: str, content: Dict):
    customer = Customer(**content.get('customer')) if event_type.split('_')[0] == 'customer' or event_type.split('_')[0] == 'subscription' else ''
    subscription = Subscription(**content.get('subscription')) if event_type.split('_')[0] == 'subscription' else ''
    payment = Payment(**content) if event_type.split('_')[0] == 'payment' and event_type.split('_')[1] != 'source' else ''
    payment_source = PaymentSource(**content.get('customer')) if event_type.split('_')[0] == 'payment' and event_type.split('_')[1] == 'source' else ''
    invoice = Invoice(**content.get('invoice')) if event_type.split('_')[0] == 'invoice' else ''

    if event_type.split('_')[0] == 'customer':
        if customer.id == '':
            return res_body(status_code=422, msg=f"Customer ID is empty.", data=f"{ 'id', customer.id }", api_src='chargebee')
                
    if event_type.split('_')[0] == 'subscription':
        if customer.id == '' or subscription.id == '':
            return res_body(status_code=422, msg=f"{ 'Subscription ID' if subscription.id == '' else 'Customer ID' } is empty.", data=f"{ 'id', subscription.id if subscription.id == '' else customer.id }", api_src='chargebee')
        
    if event_type.split('_')[0] == 'payment':
        if event_type.split('_')[1] == 'source':
            if payment_source.id == '':
                return res_body(status_code=422, msg=f"Payment Source ID is empty.", data=f"{ 'id', payment_source.id }", api_src='chargebee')
        else:
            if payment.customer.id == '' or payment.subscription.id == '' or payment.invoice.id == ''  or payment.transaction.id == '':
                return res_body(status_code=422, msg=f"Payment Customer ID is empty.", data=f"{ 'id', payment.customer.id }", api_src='chargebee')
            
    if event_type.split('_')[0] == 'invoice':
        if invoice.id == '' or invoice.customer_id == '':
            return res_body(status_code=422, msg=f"{ 'Invoice ID' if invoice.id == '' else 'Customer ID' } is empty.", data=f"{ 'id', invoice.id if invoice.id == '' else invoice.customer_id }", api_src='chargebee')
        
    logger.debug(f"Validation: { event_type.title().replace('_', ' ') } Success!")

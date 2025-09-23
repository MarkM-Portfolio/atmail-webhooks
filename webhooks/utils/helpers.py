from fastapi import HTTPException
from fastapi.responses import JSONResponse
from webhooks.models.chargebee import Customer, Subscription
from webhooks.models.mailserver import MailServer
from webhooks.models.response import ResponseBody, CustomException
from typing import Dict, List, Optional, Union
from datetime import datetime, timezone
import time, os, logging, requests


log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO), format="\n%(asctime)s - %(name)s - \n[%(levelname)s] - %(message)s\n")
logger = logging.getLogger(__name__)

event_type = str
event_time = object


def mailserver_api(secrets, method, action, customer: Union[Customer, str], data):
    headers = { 'Content-Type': 'application/json', 'Accept': 'application/json' }
    # query here customer_id to get Customer object or email
    params = { 'username': customer if isinstance(customer, str) else customer.email }
    logger.debug(f"Mail Server Account: { params } | Method: { method }")

    if method == 'GET':
        try:
            result = requests.get(f"{ secrets.get('api_url') }/accounts/{ action }", auth=(secrets.get('username'), secrets.get('password')), headers=headers, params=params, verify=True).json()
            if result.get('status') != 'success':
                raise Exception(result.get('response').get('message'))
        except (Exception) as e:
            status_code = 501 if str(e).__contains__('Specify accountId/username argument') else 500
            msg = 'Customer does not exist' if isinstance(customer, str) and status_code == 501 else f'Customer: `{ customer.email }` does not exist' if status_code == 501 else ''
            return res_body(status_code=status_code, msg=msg, data=None, api_src='mailserver')
                
    if method == 'POST':
        try:
            params.update(data)
            if data is None:
                raise Exception(f"API POST Error ({ action }). No data parameters")
        except (Exception) as e:
            return res_body(status_code=422, msg=str(e), data=data, api_src='mailserver')
        
        logger.debug(f"{ method } params: { params }")

        try:
            result = requests.post(f"{ secrets.get('api_url') }/accounts/{ action }", auth=(secrets.get('username'), secrets.get('password')), headers=headers, params=params, verify=True).json()
            if result.get('status') != 'success':
                raise Exception(result.get('response').get('message'))
        except (Exception) as e:
            status_code = 501 if str(e).__contains__('does not exist') else 500
            return res_body(status_code=status_code, msg=str(e) if status_code != 500 else '', data=data if status_code != 500 else None, api_src='mailserver')

    response = result.get('response').get('results')
    status_code = 200 if method == 'GET' else 201

    return status_code, action, data, MailServer(**response) if method == 'GET' else response

def res_body(status_code: int, msg: str, data: Dict=None, object: ResponseBody=None, api_src: str=None):
    event_time_start, event_time_end, duration = timer(timer='stop')

    logger.debug(f'[Msg: ] { msg }')
    logger.debug(f'[Data: ] { data if data else None }')
    logger.debug(f'[Object: ] { object if object else None }')
    
    if status_code == 200 or status_code == 201:
        status_reason = 'Ok'
    if status_code == 400:
        status_reason = 'Bad Request'
    if status_code == 403:
        status_reason = 'Forbidden'
    if status_code == 404:
        status_reason = 'Not Found'
    if status_code == 422:
        status_reason = 'Unprocessable Content'
    if status_code == 500:
        status_reason = 'Internal Server Error'
    if status_code == 501:
        status_reason = 'Not Implemented'
    if status_code == 502:
        status_reason = 'Bad Gateway'

    customer = Customer(**data.get('customer')) if data and data.get('customer') else None
    subscription = Subscription(**data.get('subscription')) if data and data.get('subscription') else None

    response_log = {
        'status_code': status_code,
        'status_reason': status_reason,
        'message': msg,
        'event_type': event_type.title().replace('_', ' ') if event_type else None,
        'event_started': event_time_start,
        'event_ended': event_time_end,
        'duration': duration
    }

    response_log.update({ 'customer': { 'id': customer.id, 'email': customer.email } }) if customer else None
    response_log.update({ 'subscription': { 'id': subscription.id, 'status': subscription.status } }) if subscription else None

    logger.debug('\n\t> ' + '\n\t> '.join(f'{ k.title().replace('_', ' ') }\t: ' + 
        ('\n\t     -' + '\n\t     -'.join(f'\t{ sub_k }\t: { sub_v }' for sub_k, sub_v in v.items())  
        if isinstance(v, dict) else str(v)) for k, v in response_log.items()))
    
    response = f'Response({ response_log.get('status_code') }) { response_log.get('status_reason') }: { response_log.get('message') } || @{ duration }]'

    if not 200 <= status_code < 300:
        try:
            raise CustomException(status_code, msg, data, api_src)
        except (CustomException):
            logger.error(f'Response: { response_log }')
                        
            return JSONResponse(status_code=status_code, content=response)
        finally:
            # only if CustomException still has errors force execute HTTPException
            raise HTTPException(status_code=status_code, detail=response)

    logger.info(f'Response: { response_log }')

    return response

def timer(event: str=None, timer: str=None):
    if timer == 'start':
        global event_type
        global event_time
        event_type = event
        event_time = datetime.fromtimestamp(time.time(), timezone.utc)
                
    dt_object = datetime.fromtimestamp(time.time(), timezone.utc)
    date_str = dt_object.strftime('%m/%d/%Y') if timer == 'stop' else event_time.strftime('%m/%d/%Y') if timer == 'start' else None
    time_str = dt_object.strftime('%H:%M:%S (%Z)') if timer == 'stop' else event_time.strftime('%H:%M:%S (%Z)') if timer == 'start' else None
    event_time_start = f'{ date_str } { time_str }' if timer == 'start' else event_time.strftime('%m/%d/%Y %H:%M:%S (%Z)') if timer == 'stop' else None

    if timer == 'stop':
        dt_difference = (dt_object - event_time)
        event_time_end = f'{ date_str } { time_str }'
        hours, remainder = divmod(dt_difference.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = round(dt_difference.microseconds // 1000) % 100
        duration = f'{ hours }h { minutes }m { seconds }s' if hours > 0 else f'{ minutes }m { seconds }s' if minutes > 0 else f'{ seconds }.{ milliseconds } secs'

    return event_time_start if timer == 'start' else (event_time_start, event_time_end, duration) if timer == 'stop' else None

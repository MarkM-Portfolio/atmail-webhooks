from pydantic import BaseModel
from .mailserver import MailServer
from typing import Dict, List, Optional, Union


class ResponseBody(BaseModel):
    status_code: int
    msg: Optional[str] = None
    data: Optional[Dict] = None
    object: Optional[Union[ Dict, MailServer ]] = None
    api_src: Optional[str] = None

class CustomException(Exception):
    def __init__(self, status_code: int, msg: str, data: Dict, api_src: str):
        status_code = status_code
        msg = msg
        data = data
        api_src = api_src
        
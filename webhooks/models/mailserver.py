from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional, Union
from datetime import datetime


class Profile(BaseModel):
    id: int
    name: str
    active: bool

class CosProfile(BaseModel):
    profile: List[ Profile ]
    origin: str

class MailServer(BaseModel):
    accountId: str
    username: EmailStr
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    account_status: Optional[str] = None
    password_status: Optional[str] = None
    userStatus: Optional[str] = None
    cosProfile: List[ CosProfile ]
    domainId: Optional[str] = None
    createdByUserId: Optional[str] = None
    dateModified: Optional[datetime] = None
    dateCreate: Optional[datetime] = None
    migrateStatus: Optional[str] = None
    forward: Optional[str] = None
    quota: Optional[str] = None
    masterQuota: Optional[str] = None
    lastLogin: Optional[str] = None
    groupId: Optional[str] = None
    mboxServer: Optional[str] = None
    mboxType: Optional[str] = None
    billingCode: Optional[str] = None
    password_set_on: Optional[Union[datetime, str]] = None
    expiry: Optional[str] = None
    totpStatus: Optional[str] = None
    UsedQuota: Optional[Union[int, float]] = None
    TotalMessages: Optional[Union[int, float]] = None
    totalQuotaBytes: Optional[Union[int, float]] = None
    mailUsedBytes: Optional[Union[int, float]] = None
    fileUsedBytes: Optional[Union[int, float]] = None
    totalFiles: Optional[Union[int, float]] = None
    quotaStatus: Optional[str] = None
    disableQuotaCheck: Optional[str] = None
    account_status_updated_at: Optional[datetime] = None
    
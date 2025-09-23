from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional, Union
from datetime import datetime


class BillingAddress(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip: Optional[str] = None
    validation_status: Optional[str] = None
    object: str

class LineItems(BaseModel):
    id: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    unit_amount: Optional[int] = None
    quantity: Optional[int] = None
    amount: Optional[int] = None
    pricing_model: Optional[str] = None
    is_taxed: Optional[bool] = None
    tax_amount: Optional[int] = None
    subscription_id: Optional[str] = None
    customer_id: Optional[str] = None
    description: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    tax_exempt_reason: Optional[str] = None
    discount_amount: Optional[int] = None
    item_level_discount_amount: Optional[int] = None
    object: str

class Balances(BaseModel):
    promotional_credits: Optional[int] = None
    excess_payments: Optional[int] = None
    refundable_credits: Optional[int] = None
    unbilled_charges: Optional[int] = None
    currency_code: Optional[str] = None
    balance_currency_code: Optional[str] = None
    object: str

class LinkedInvoices(BaseModel):
    invoice_id: int
    applied_amount: Optional[int] = None
    applied_at: Optional[datetime] = None
    invoice_date: Optional[datetime] = None
    invoice_total: Optional[int] = None
    invoice_status: Optional[str] = None

class LinkedPayments(BaseModel):
    txn_id: Optional[str] = None
    applied_amount: Optional[int] = None
    applied_at: Optional[datetime] = None
    txn_status: Optional[str] = None
    txn_date: Optional[datetime] = None
    txn_amount: Optional[int] = None

class PaymentMethod(BaseModel):
    id: Optional[str] = None
    gateway: Optional[str] = None
    gateway_account_id: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None
    reference_id: Optional[str] = None
    object: str

class Card(BaseModel):
    status: Optional[str] = None
    gateway: Optional[str] = None
    gateway_account_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    iin: Optional[str] = None
    last4: Optional[int] = None
    card_type: Optional[str] = None
    funding_type: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    issuing_country: Optional[str] = None
    billing_addr1: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_country: Optional[str] = None
    billing_zip: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    powered_by: Optional[str] = None
    resource_version: Optional[datetime] = None
    masked_number: Optional[str] = None
    customer_id: Optional[str] = None
    payment_source_id: Optional[str] = None
    object: str

class PaymentSource(BaseModel):
    id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    locale: Optional[str] = None
    phone: Optional[str] = None
    auto_collection: Optional[str] = None
    net_term_days: Optional[int] = None
    allow_direct_debit: Optional[bool] = None
    created_at: Optional[datetime] = None
    created_from_ip: Optional[str] = None
    taxability: Optional[str] = None
    updated_at: Optional[datetime] = None
    pii_cleared: Optional[str] = None
    channel: Optional[str] = None
    resource_version: Optional[datetime] = None
    deleted: Optional[bool] = None
    billing_address: Optional[ BillingAddress ] = None
    card_status: Optional[str] = None
    balances: Optional[List[ Balances ]] = None
    promotional_credits: Optional[int] = None
    refundable_credits: Optional[int] = None
    excess_payments: Optional[int] = None
    unbilled_charges: Optional[int] = None
    preferred_currency_code: Optional[str] = None
    mrr: Optional[int] = None
    primary_payment_source_id: Optional[str] = None
    payment_method: Optional[ PaymentMethod ] = None
    object: str

class Invoice(BaseModel):
    id: int
    customer_id: str
    subscription_id: str
    recurring: Optional[bool] = None
    status: Optional[str] = None
    price_type: Optional[str] = None
    date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    net_term_days: Optional[int] = None
    exchange_rate: Optional[Union[int, float]] = None
    total: Optional[int] = None
    amount_paid: Optional[int] = None
    amount_adjusted: Optional[int] = None
    write_off_amount: Optional[int] = None
    credits_applied: Optional[int] = None
    amount_due: Optional[int] = None
    paid_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    resource_version: Optional[datetime] = None
    deleted: Optional[bool] = None
    first_invoice: Optional[bool] = None
    amount_to_collect: Optional[int] = None
    round_off_amount: Optional[int] = None
    new_sales_amount: Optional[int] = None
    has_advance_charges: Optional[bool] = None
    currency_code: Optional[str] = None
    base_currency_code: Optional[str] = None
    generated_at: Optional[datetime] = None
    is_gifted: Optional[bool] = None
    term_finalized: Optional[bool] = None
    channel: Optional[str] = None
    tax: Optional[int] = None
    line_items: Optional[List[ LineItems ]] = None
    sub_total: Optional[int] = None
    linked_payments: Optional[List[ LinkedPayments ]] = None
    applied_credits: Optional[List] = None
    adjustment_credit_notes: Optional[List] = None
    issued_credit_notes: Optional[List] = None
    linked_orders: Optional[List] = None
    dunning_attempts:Optional[List] = None
    billing_address: Optional[ BillingAddress ] = None
    site_details_at_creation: Optional[Dict] = { 'timezone': str }
    object: str

class Transaction(BaseModel):
    id: str
    customer_id: str
    subscription_id: str
    gateway_account_id: Optional[str] = None
    payment_source_id: Optional[str] = None
    payment_method: Optional[str] = None
    gateway: Optional[str] = None
    type: Optional[str] = None
    date: Optional[datetime] = None
    exchange_rate: Optional[Union[int, float]] = None
    amount: Optional[int] = None
    id_at_gateway: Optional[str] = None
    status: Optional[str] = None
    updated_at: Optional[datetime] = None
    resource_version: Optional[datetime] = None
    deleted: Optional[bool] = None
    currency_code: Optional[str] = None
    base_currency_code: Optional[str] = None
    amount_unused: Optional[int] = None
    linked_invoices: Optional[List[ LinkedInvoices ]] = None
    linked_refunds: Optional[List] = None
    object: str

class Customer(BaseModel):
    id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    locale: Optional[str] = None
    billing_address: Optional[BillingAddress] = None
    cf_consent_to_transfer_account: Optional[datetime] = None
    cf_final_user_migration_time: Optional[datetime] = None
    cf_already_paying_with_provider: Optional[str] = None
    cf_legacy_provider: Optional[str] = None
    cf_sms_opted_out: Optional[str] = None
    cf_has_selected_a_paid_plan: Optional[str] = None
    cf_reactivation_service_exempted: Optional[str] = None
    cf_customer_passcode: Optional[str] = None

class SubscriptionItems(BaseModel):
    item_price_id: str
    item_type: str
    quantity: int
    unit_price: int
    amount: int
    free_quantity: int
    object: str

class Subscription(BaseModel):
    id: str
    customer_id: str
    status: str
    subscription_items: Optional[List[ SubscriptionItems ]] = None
    billing_period: Optional[int] = None
    billing_period_unit: Optional[str] = None
    current_term_start: Optional[datetime] = None
    current_term_end: Optional[datetime] = None
    next_billing_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    created_from_ip: Optional[str] = None
    updated_at: Optional[datetime] = None
    has_scheduled_changes: Optional[bool] = None
    channel: Optional[str] = None
    resource_version: Optional[datetime] = None
    deleted: Optional[bool] = None
    currency_code: Optional[str] = None
    due_invoices_count: Optional[int] = None
    mrr: Optional[int] = None
    exchange_rate: Optional[Union[int, float]] = None
    base_currency_code: Optional[str] = None
    has_scheduled_advance_invoices: Optional[bool] = None
    cf_Update_Subscription_Toggle: Optional[str] = None
    object: str

class Payment(BaseModel):
    transaction: Transaction
    invoice: Invoice
    customer: Customer
    subscription: Subscription

class ChargebeeWebhookPayload(BaseModel):
    event_type: str
    webhook_status: str
    content: Dict

# Part of Odoo. See LICENSE file for full copyright and licensing details.

# ISO 4217 codes of currencies supported by Flooss
SUPPORTED_CURRENCIES = (
    'AED',  # UAE Dirham
    'SAR',  # Saudi Riyal
    'USD',  # US Dollar
)

# The codes of the payment methods to activate when Flooss is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    'flooss',
}

# Mapping of Flooss payment API status (uppercase as per API docs) to Odoo payment states.
PAYMENT_STATUS_MAPPING = {
    'PENDING': 'pending',
    'CREATED': 'pending',
    'AWAITING_APPROVAL': 'pending',
    'SUCCESS': 'done',
    'COMPLETED': 'done',
    'CANCELLED': 'cancel',
    'DECLINED': 'cancel',
    'VOIDED': 'cancel',
    'FAILED': 'error',
    'ERROR': 'error',
}

# Events handled by webhook notifications (update if Flooss changes webhook event names)
HANDLED_WEBHOOK_EVENTS = [
    'PAYMENT.COMPLETED',
    'PAYMENT.APPROVED',
    'PAYMENT.REVERSED',
]

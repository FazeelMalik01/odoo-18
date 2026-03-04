# Part of Odoo. See LICENSE file for full copyright and licensing details.

def get_normalized_email_account(provider):
    """
    Remove unicode characters (like zero-width spaces) from Flooss merchant email account.

    :param provider: The payment provider record (Flooss)
    :return: Normalized ASCII email address
    :rtype: str
    """
    return (provider.flooss_merchant_email or '').encode('ascii', 'ignore').decode('utf-8')

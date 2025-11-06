# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint
import requests
import uuid
import base64
import os
from datetime import timedelta
from werkzeug import urls
import requests_toolbelt.multipart.encoder as multipart_encoder
import uuid
from odoo.addons.payment_flooss import const


from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('flooss', "Flooss")], ondelete={'flooss': 'set default'}
    )
    flooss_merchant_email = fields.Char(
        string="Flooss Merchant Email",
        help="The public business email used to identify the account with Flooss",
        required_if_provider='flooss',
        default=lambda self: self.env.company.email,
    )
    flooss_merchant_password = fields.Char(
    string="Flooss Merchant Password",
    required_if_provider='flooss',
    groups='base.group_system',
    password=True,
)
    flooss_merchant_id = fields.Char(string="Flooss Merchant ID", required_if_provider='flooss')
    flooss_client_id = fields.Char(string="Flooss Client ID", required_if_provider='flooss')
    flooss_client_secret = fields.Char(string="Flooss Client Secret", groups='base.group_system')
    flooss_access_token = fields.Char(
        string="Flooss Access Token",
        help="Short-lived access token to call Flooss APIs",
        groups='base.group_system',
    )
    flooss_access_token_expiry = fields.Datetime(
        string="Flooss Access Token Expiry",
        default='1970-01-01',
        groups='base.group_system',
    )
    flooss_webhook_id = fields.Char(string="Flooss Webhook ID")
    flooss_notify_jwt = fields.Char(string="Flooss Notify JWT Token", groups='base.group_system')

    # === URLs from API contract ===
    _prod_base_url = 'https://mapp.flooss.com'
    _uat_base_url = 'https://testflooss.tamhere.com'

    def _flooss_get_base_url(self):
        self.ensure_one()
        if self.state == 'enabled':
            return self._prod_base_url
        else:
            return self._uat_base_url

    def _flooss_make_request(self, endpoint, data=None, json_payload=None, headers=None,  is_refresh_token_request=False, idempotency_key=None, method='POST'):
        self.ensure_one()
        url = urls.url_join(self._flooss_get_base_url(), endpoint)
        if headers is None:
            headers = {}

        if idempotency_key:
            headers['Flooss-Request-Id'] = idempotency_key

        if not is_refresh_token_request:
            # Use access token, refresh if expired
            token = self._flooss_fetch_access_token()
            headers['Authorization'] = f'Bearer {token}'

        try:
            if method.upper() == 'POST':
                response = requests.post(url, headers=headers, data=data, json=json_payload, timeout=10)
            elif method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=data, json=json_payload,  timeout=10)
            else:
                raise ValidationError(_("Unsupported HTTP method for Flooss API call: %s") % method)

            try:
                response.raise_for_status()
                response_code = response.status_code
                if response_code == 200:
                    _logger.info(" Request OK - Status: %s", response_code)


                elif response_code == 400:
                    _logger.error("Request failed - Bad Request - Status: %s", response_code)
                    # Handle bad request

                elif response_code == 401:
                    _logger.error("Request failed - Unauthorized access - Status: %s", response_code)
                    _logger.error("Check API credentials and authentication tokens")
                    # Handle unauthorized access

                elif response_code == 403:
                    _logger.error("Request failed - Forbidden access - Status: %s", response_code)
                    _logger.error("Insufficient permissions or API key restrictions")
                    # Handle forbidden access

                elif response_code == 404:
                    _logger.error("Request failed - Resource not found - Status: %s, URL: %s", response_code,
                                  url)


                elif response_code == 417:
                    _logger.error("Payment request failed - Expectation Failed - Status: %s", response_code)
                    _logger.error("Server cannot meet the requirements of the Expect request header")
                    _logger.error("Check request headers and server capabilities")

                else:
                    _logger.warning("Payment request returned unexpected status code: %s", response_code)
                    _logger.warning("Response content: %s", response.text[:500])
            except requests.exceptions.HTTPError:
                payload = data or json_payload
                _logger.exception("Invalid API request at %s with data:\n%s", url, pprint.pformat(payload))
                # Try to extract error message safely
                try:
                    error_msg = response.json().get('message', '')
                except Exception:
                    error_msg = response.text or 'No error message received'
                raise ValidationError(_("Flooss API communication failed. Details: %s") % error_msg)

            # Try to parse JSON response safely
            try:
                if response.content:
                    return response.json()
                else:
                    _logger.warning("Empty response content from Flooss API at %s", url)
                    return {}
            except ValueError:
                _logger.error("Invalid JSON response from Flooss API at %s: %s", url, response.text)
                raise ValidationError(_("Flooss API returned invalid or malformed JSON response."))

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach Flooss API endpoint at %s", url)
            raise ValidationError(_("Could not establish the connection to the Flooss API."))


    def _flooss_fetch_access_token(self):
        self.ensure_one()


        if fields.Datetime.now() > self.flooss_access_token_expiry - timedelta(minutes=5):
            base_url = self._flooss_get_base_url()
            url = urls.url_join(base_url, '/pie/api/v1/oauth/token')

            multipart_data = multipart_encoder.MultipartEncoder(
                fields={
                    'username': self.flooss_merchant_email,
                    'password': self.flooss_merchant_password,
                    'grant_type': 'password',
                    'scope': 'back_office',
                    'client_id': self.flooss_client_id,
                    'client_secret': self.flooss_client_secret,
                    'device_type': 'WEB',
                    'device_token': str(uuid.uuid4()),
                }
            )

            headers = {
                'Content-Type': multipart_data.content_type,
            }

            response = requests.post(url, data=multipart_data, headers=headers, timeout=10)
            response_code =response.status_code
            try:
                if response_code == 200:
                    _logger.info("Authenticate request successful - Status: %s", response_code)
                    # Handle successful response
                    response_data = response.json()
                    _logger.debug("Response data: %s", response_data)

                elif response_code == 401:
                    _logger.error("Unauthorized access - Status: %s", response_code)
                    _logger.error("Check API credentials and authentication tokens")
                    # Handle unauthorized access

                elif response_code == 403:
                    _logger.error("Request failed - Forbidden access - Status: %s", response_code)
                    _logger.error("Insufficient permissions or API key restrictions")
                    # Handle forbidden access

                elif response_code == 404:
                    _logger.error("Request failed - Resource not found - Status: %s, URL: %s", response_code,
                                  url)
                    _logger.error("Check the API endpoint URL and payment gateway configuration")
                    # Handle not found

                else:
                    _logger.warning("Payment request returned unexpected status code: %s", response_code)
                    _logger.warning("Response content: %s", response.text[:500])  # L
            except requests.exceptions.HTTPError:
                _logger.exception("Error fetching Flooss token at %s", url)
                raise ValidationError(_("Failed to get Flooss access token."))

            response_content = response.json()
            access_token = response_content.get('access_token')
            if not access_token:
                raise ValidationError(_("Could not generate a new access token from Flooss."))

            self.write({
                'flooss_access_token': access_token,
                'flooss_access_token_expiry': fields.Datetime.now() + timedelta(seconds=response_content.get('expires_in', 120)),
            })

        return self.flooss_access_token
    
    def _flooss_get_inline_form_values(self, currency=None):
        """Return JSON string of the values needed for the Flooss inline form."""
        currency_code = currency.name if currency and currency.name in const.SUPPORTED_CURRENCIES else 'USD'
        inline_form_values = {
            'provider_id': self.id,
            'client_id': self.flooss_client_id or 'DEFAULT_CLIENT_ID',
            'currency_code': currency_code,
        }
        return json.dumps(inline_form_values)
        


    # ==== FLOOSS API wrappers ====

    def _flooss_request_otp(self, phone):
        payload = {'phoneNumber': phone}
        return self._flooss_make_request(
            '/pie/api/v1/bo/merchants/verify-flooss-account-with-otp',
            json_payload=payload
        )

    def _flooss_encrypt_otp(self, otp):
        """
        Encrypt the OTP using Flooss encrypt-string API.
        Uses AES key from system parameters.
        Returns the encrypted OTP string.
        """
        self.ensure_one()

        # Get AES key from system parameters
        aes_key = self.env['ir.config_parameter'].sudo().get_param('flooss.aes_key')
        if not aes_key:
            raise ValidationError(_("Flooss AES key is not configured"))

        # Prepare payload
        payload = {
            "stringToBeEncrypted": otp,
            "key": aes_key,
        }

        # Call Flooss encrypt-string API
        try:
            response = self._flooss_make_request(
                '/pie/api/v1/bo/merchants/encrypt-string',
                json_payload=payload
            )
        except ValidationError as e:
            raise ValidationError(_("Failed to encrypt OTP via Flooss: %s") % e)

        # If the API returned a string, just use it
        if isinstance(response, str):
            encrypted_otp = response
        elif isinstance(response, dict):
            encrypted_otp = response.get('encryptedString')
        else:
            raise ValidationError(_("Unexpected response from Flooss encrypt-string API."))

        if not encrypted_otp:
            raise ValidationError(_("Flooss did not return an encrypted OTP."))

        return encrypted_otp




    def _flooss_verify_otp(self, phone, encrypted_otp):
        payload = {
            'phoneNumber': phone,
            'encryptedOtp': encrypted_otp,
        }
        return self._flooss_make_request(
            '/pie/api/v1/bo/merchants/verify-customer-otp',
            json_payload=payload
        )

    def _flooss_send_payment_request(self, tx_sudo=None, phone=None):
        # if not tx_sudo or not phone:
        #     raise ValidationError(_("Cannot send Flooss payment request before OTP verification."))
        sale_order = tx_sudo.sale_order_ids[:1]  # take first linked SO
        merchant_order_id = (sale_order.name or tx_sudo.reference).replace("/", "")
        payload = {
            'merchantId': int(self.flooss_merchant_id),
            'transactionAmount': float(tx_sudo.amount),
            'phoneNumber': phone,
            'merchantTransactionType': 'ONLINE_CHECKOUT',
            'merchantOrderId': merchant_order_id,
        }
            # 👇 log payload before sending to Flooss
        _logger.info("Sending Flooss payment request with payload: %s", payload)
        idempotency_key = tx_sudo.reference or str(uuid.uuid4())
        return self._flooss_make_request(
            '/pie/api/v1/bo/merchants/payment-request',
            json_payload=payload,
            idempotency_key=idempotency_key,
        )


    # def action_flooss_create_webhook(self):
    #     self.ensure_one()
    #     try:
    #         # Construct webhook URL where Flooss will send notifications
    #         webhook_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/pie/api/v1/payment/flooss/webhook'
    #         payload = {
    #             'webhookUrl': webhook_url,
    #         }
    #         response = self._flooss_make_request(
    #             '/pie/api/v1/bo/merchants/webhooks',  # Confirm this endpoint in Flooss API docs
    #             json_payload=payload,
    #             method='GET'
    #         )
    #         webhook_id = response.get('id') or response.get('webhookId') or 'unknown'
    #         self.write({'flooss_webhook_id': webhook_id})
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'title': 'Success',
    #                 'message': f'Webhook created with ID: {webhook_id}',
    #                 'type': 'success',
    #                 'sticky': False,
    #             }
    #         }
    #     except Exception as e:
    #         raise ValidationError(f"Failed to create webhook: {e}")

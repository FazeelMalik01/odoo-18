# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software PVT. LTD.
# See LICENSE file for full copyright & licensing details.

from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


# Controller for handling OTP generation, verification, and partner verification using Twilio SMS.
class Otp(http.Controller):
    @http.route(["/otp"], type="json", auth="public", website="True")
    def otp(self, phone):
        normalized_phone = phone.lstrip("+")
        sms = request.env["smsapril.sms"].create({"ph_number": normalized_phone})
        rec_list = sms.create_sms()
        return rec_list

    @http.route(["/otp/verify"], type="json", auth="public", website="True")
    def otp_verify(self, phone, otp_value):
        # normalize phone -> remove leading "+"
        normalized_phone = phone.lstrip("+")
        sms = request.env["smsapril.sms"].search(
            [("ph_number", "=", normalized_phone)], order="id desc", limit=1
        )

        if sms and sms.otp == otp_value:
            if not sms.is_otp_valid:
                _logger.warning("⚠️ OTP matches but SMS was not delivered (error=%s)", sms.error_message)
            return True

    @http.route(["/partner_verify/otp"], type="json", auth="public", website="True")
    def partner_verify_otp(self, phone, check_phone):
        partner = (
            request.env["res.partner"]
            .sudo()
            .search([("mobile", "=", check_phone)], limit=1)
        )

        if partner:
            sms = request.env["smsapril.sms"].create({"ph_number": phone})
            sms.create_sms()
            return True
        else:
            partner = (
                request.env["res.partner"]
                .sudo()
                .search([("mobile", "=", phone)], limit=1)
            )
            if partner:
                sms = request.env["smsapril.sms"].create({"ph_number": phone})
                sms.create_sms()
                return True
            return False

    @http.route(["/otp/reset"], type="json", auth="public", website="True")
    def reset_url_create(self, phone, check_phone):
        
        partner = request.env["res.partner"].sudo().search([("mobile", "=", phone)], limit=1)
        if partner:
            partner.signup_custom_prepare()  # sets signup_type="reset"
            
            if not partner.user_ids:
                partner.signup_prepare()  # only for new users
        
            partner.with_context(signup_force_type_in_url='reset').compute_custom_signup_url()
            return partner.custom_signup_url
        else:

            partner = request.env["res.partner"].sudo().search([("mobile", "=", check_phone)], limit=1)
            if partner:
                partner.signup_custom_prepare()
                
                if not partner.user_ids:
                    partner.signup_prepare()
                
                partner.with_context(signup_force_type_in_url='reset').compute_custom_signup_url()
                return partner.custom_signup_url
            else:
                return False

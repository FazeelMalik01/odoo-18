# -*- coding: utf-8 -*-
from odoo import models, fields
from datetime import datetime, timedelta
import random as r
import requests
import logging
import re
from datetime import datetime

_logger = logging.getLogger(__name__)


class SMSApril(models.Model):
    _name = "smsapril.sms"
    _description = "SMSApril OTP SMS"

    error_message = fields.Text("Error Message", copy=False, readonly=1)
    state = fields.Selection([("sent", "Sent"), ("error", "Error")], string="State")
    otp = fields.Char(string="OTP")
    ph_number = fields.Char(string="Phone number")
    expiry_date = fields.Datetime(string="Expiry Date")
    is_otp_valid = fields.Boolean(compute="otp_validity")
    resend_count = fields.Integer(string="Resend Count", default=0)

    def create_sms(self):
        """Send OTP via SMSApril API"""
        param_obj = self.env["ir.config_parameter"]
        username = param_obj.sudo().get_param("smsapril.username")
        password = param_obj.sudo().get_param("smsapril.password")
        sender = param_obj.sudo().get_param("smsapril.sender")
        now = datetime.now()
        current_date = now.strftime("%m/%d/%Y")  # e.g., 09/10/2025
        current_time = now.strftime("%H:%M") 
        _logger.info("🔧 SMSApril config -> user=%s, sender=%s", username, sender)

        if not username or not password or not sender:
            _logger.error("❌ Missing SMSApril configuration parameters")
            return ["config_parameter"]

        # Generate OTP
        self.expiry_date = datetime.now() + timedelta(seconds=5)
        new_otp = "".join(str(r.randint(0, 9)) for _ in range(6))
        self.otp = new_otp

        # Build SMS body
        body = f"{self.otp} is your PEPTIDAT verification code. Valid for 5 minutes."

        # --- FIX: clean phone number ---
        phone_number = re.sub(r"[^\d]", "", self.ph_number or "")
        _logger.info("📱 Cleaned phone number for SMSApril: %s (raw=%s)", phone_number, self.ph_number)

        # Prepare API call
        url = "http://www.smsapril.com/api.php"
        params = {
            "comm": "sendsms",
            "user": username,
            "pass": password,
            "to": phone_number,
            "message": body,
            "sender": sender,
            "date": current_date,
            "time": current_time,
        }
        _logger.info("📡 Sending SMS via AprilSMS with date/time -> %s %s", current_date, current_time)
        # Log final request details
        debug_url = f"{url}?comm=sendsms&user={username}&pass={password}&to={phone_number}&message={body}&sender={sender}"
        _logger.info("📡 Sending SMS via AprilSMS -> %s", debug_url)

        try:
            response = requests.get(url, params=params, timeout=10)
            _logger.info("📩 SMSApril raw response: %s", response.text.strip())

            if response.text.strip().startswith("1") or response.text.strip().startswith("999"):
                state = "sent"
                error_message = None
            else:
                state = "error"
                error_message = f"SMSApril error: {response.text}"

            self.write({"error_message": error_message, "state": state})
            return [state == "sent", response.text, body]

        except Exception as e:
            _logger.error("🚨 SMSApril OTP exception: %s", str(e))
            self.write({"error_message": str(e), "state": "error"})
            return [False, None, str(e)]

    def otp_validity(self):
        for rec in self:
            rec.is_otp_valid = bool(rec.expiry_date and rec.expiry_date > datetime.now())

    def otp_sms_record_cleaner(self):
        self.search([("expiry_date", "<", datetime.now())]).unlink()

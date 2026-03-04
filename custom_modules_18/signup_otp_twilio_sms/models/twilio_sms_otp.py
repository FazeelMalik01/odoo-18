# # -*- coding: utf-8 -*-
# # Part of Odoo, Aktiv Software PVT. LTD.
# # See LICENSE file for full copyright & licensing details.

# from odoo import models, fields
# from datetime import datetime, timedelta
# import random as r
# from twilio.rest import Client


# class TwilioSMS(models.Model):
#     """This class is to create new model twilio.sms"""

#     _name = "twilio.sms"
#     _description = "twilio sms"

#     error_message = fields.Text("Error Message", copy=False, readonly=1)
#     state = fields.Selection([("sent", "Send"), ("error", "Error")], string="State")
#     otp = fields.Char(string="OTP")
#     ph_number = fields.Char(string="Phone number")
#     expiry_date = fields.Datetime(string="Expiry Date")
#     is_otp_valid = fields.Boolean(compute="otp_validity")

#     def create_sms(self):
#         # To send OTP
#         param_obj = self.env["ir.config_parameter"]
#         twilio_account_sid = param_obj.sudo().get_param("twilio_sms.twilio_account_sid")
#         twilio_auth_token = param_obj.sudo().get_param("twilio_sms.twilio_auth_token")
#         twilio_from_number = param_obj.sudo().get_param("twilio_sms.twilio_from_number")

#         if not twilio_account_sid or not twilio_auth_token or not twilio_from_number:

#             return ["config_parameter"]

#         if twilio_account_sid and twilio_auth_token and twilio_from_number:
#             self.expiry_date = self.create_date + timedelta(minutes=5)

#             client = Client(twilio_account_sid, twilio_auth_token)
#             new_otp = ""
#             for i in range(6):
#                 new_otp += str(r.randint(1, 9))
#             self.otp = new_otp
#             body = (
#                 self.otp
#                 + " is the OTP Verification Code for request of Odoo account signup/reset password. This is valid for 5 minutes."
#             )
#             try:
#                 response = client.messages.create(
#                     body=body, from_=twilio_from_number, to=self.ph_number
#                 )

#                 if response.error_message:
#                     state = "error"
#                     error_message = response.error_message
#                 else:
#                     state = "sent"
#                     error_message = None

#                 # update msg in DB and return list as per needed
#                 self.write({"error_message": error_message, "state": state})
#                 return [
#                     True,
#                     response.__dict__.get("stataus"),
#                     response.__dict__.get("msg"),
#                 ]

#             except Exception as e:
#                 state = "error"
#                 error_message = e.msg or e.__str__()

#                 # update msg in DB and return list as per needed
#                 self.write({"error_message": error_message, "state": state})
#                 return [
#                     False,
#                     e.__dict__.get("stataus"),
#                     e.__dict__.get("msg"),
#                 ]

#     def otp_validity(self):
#         for rec in self:
#             rec.is_otp_valid = rec.expiry_date and rec.expiry_date > datetime.now()

#     def otp_sms_record_cleaner(self):
#         self.env["twilio.sms"].search([("expiry_date", "<", datetime.now())]).unlink()


# """Note from twilio :
# Unable to create record: The number  is unverified. Trial accounts cannot
# send messages to unverified numbers; verify  at
# twilio.com/user/account/phone-numbers/verified, or
# purchase a Twilio number to send messages to unverified numbers."""

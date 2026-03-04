from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    smsapril_enabled = fields.Boolean(string="Enable AprilSMS Service")
    smsapril_username = fields.Char("SMSApril Username")
    smsapril_password = fields.Char("SMSApril Password")
    smsapril_sender = fields.Char("Sender Name")

    @api.model
    def get_values(self):
        res = super().get_values()
        param_obj = self.env["ir.config_parameter"].sudo()
        res.update(
            smsapril_enabled = param_obj.get_param('smsapril.enabled', 'False') == 'True',
            smsapril_username=param_obj.get_param("smsapril.username"),
            smsapril_password=param_obj.get_param("smsapril.password"),
            smsapril_sender=param_obj.get_param("smsapril.sender"),
        )
        return res
    
    @api.model
    def set_values(self):
        super().set_values()
        param_obj = self.env["ir.config_parameter"].sudo()
        param_obj.set_param('smsapril.enabled', 'True' if self.smsapril_enabled else 'False')
        param_obj.set_param("smsapril.username", self.smsapril_username)
        param_obj.set_param("smsapril.password", self.smsapril_password)
        param_obj.set_param("smsapril.sender", self.smsapril_sender)
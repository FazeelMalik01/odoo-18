from odoo import models, fields


class ResConfig(models.TransientModel):
    """res config"""
    _inherit = 'res.config.settings'
    _description = __doc__

    reminder_days = fields.Integer(string="Membership Renewal Reminder Days", default=5,
                                   config_parameter='tk_gym_management.reminder_days')

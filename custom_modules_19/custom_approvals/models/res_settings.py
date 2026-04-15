from odoo import fields, models

class SalesResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    discount = fields.Float(string="Discount (%)",  config_parameter='custom_approvals.discount')
    pm = fields.Many2one('res.users', string="Project Manager",  config_parameter='custom_approvals.pm')
    fm = fields.Many2one('res.users', string="Finance Manager",  config_parameter='custom_approvals.fm')
    ceo = fields.Many2one('res.users', string="CEO",  config_parameter='custom_approvals.ceo')

    purchase_amount = fields.Float(string="Amount",  config_parameter='custom_approvals.purchase_amount')
    purchase_pm = fields.Many2one('res.users', string="Project Manager",  config_parameter='custom_approvals.purchase_pm')
    purchase_fm = fields.Many2one('res.users', string="Finance Manager",  config_parameter='custom_approvals.purchase_fm')
    purchase_ceo = fields.Many2one('res.users', string="CEO",  config_parameter='custom_approvals.purchase_ceo')

    expense_amount = fields.Float(string="Amount",  config_parameter='custom_approvals.expense_amount')
    expense_fm = fields.Many2one('res.users', string="Finance Manager",  config_parameter='custom_approvals.expense_fm')
    expense_ceo = fields.Many2one('res.users', string="CEO",  config_parameter='custom_approvals.expense_ceo')

    timesheet_manager = fields.Many2one('res.users', string="Timesheet Manager",  config_parameter='custom_approvals.timesheet_manager')

    hr = fields.Many2one('res.users', string="HR Manager",  config_parameter='custom_approvals.hr')

    invoice_fm = fields.Many2one('res.users', string="Finance Manager",  config_parameter='custom_approvals.invoice_fm')
    invoice_ceo = fields.Many2one('res.users', string="CEO",  config_parameter='custom_approvals.invoice_ceo')
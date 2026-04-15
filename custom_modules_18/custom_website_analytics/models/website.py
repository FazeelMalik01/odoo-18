# -*- coding: utf-8 -*-
from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account',
        help="Analytic account to apply on sale order lines for orders placed on this website.",
    )
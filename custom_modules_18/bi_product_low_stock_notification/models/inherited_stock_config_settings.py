# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields,models,api, _
from ast import literal_eval
from odoo import SUPERUSER_ID
import base64

class ResConfigSettings(models.TransientModel):
	_inherit = ['res.config.settings']

	notification_product_type = fields.Selection(related='company_id.notification_product_type',string='Apply On',readonly=False)
	notification_base = fields.Selection(related='company_id.notification_base',string='Notification Based On',readonly=False)
	notification_products = fields.Selection(related='company_id.notification_products',string='Min Quantity Based On',readonly=False)
	min_quantity = fields.Float(string = 'Quantity Limit',related='company_id.min_quantity',readonly=False)
	email_user = fields.Char( string="Email From",related='company_id.email',readonly=False)
	current_user = fields.Many2one('res.users',string='current')
	report_category_id = fields.Many2one(
        related='company_id.report_category_id',
        string='Report Product Category',
        readonly=False,
        help="Filter the Low Stock Report to a specific product category. "
             "Leave empty to show all products."
    )
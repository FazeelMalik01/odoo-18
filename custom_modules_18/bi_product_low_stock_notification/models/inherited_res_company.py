# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models

class Company(models.Model):
	_inherit = 'res.company'

	notification_product_type = fields.Selection([('template','Product'),('variant','Product Variant')],default='variant',string='Apply On')

	notification_base = fields.Selection([('on_hand','On hand quantity'),('fore_cast','Forecast')],string='Notification Based On',default='on_hand')
	notification_products = fields.Selection([('for_all','Global for all product'),('fore_product',' Individual for all products'),('reorder',' Reorder Rules')],string='Min Quantity Based On',default='for_all')
	min_quantity = fields.Float(string = 'Quantity Limit')
	notify_low_stock = fields.Boolean(string="Low Stock Notification?")
	low_stock_products_ids = fields.One2many('low.stock.line','new_product_id')
	report_category_id = fields.Many2one(
        'product.category',
        string='Report Product Category',
        help="If set, the Low Stock Report will only include products from this category. "
             "Leave empty to include all products."
    )
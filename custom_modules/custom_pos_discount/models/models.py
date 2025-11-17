# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'
    
    # Add discount_amount field to store absolute discount amount
    discount_amount = fields.Float(
        string='Discount Amount', 
        digits='Product Price', 
        default=0.0,
        help="Absolute discount amount in currency"
    )
    
    @api.model
    def _load_pos_data_fields(self, config_id):
        """Override to include discount_amount in POS data loading"""
        fields = super()._load_pos_data_fields(config_id)
        if 'discount_amount' not in fields:
            fields.append('discount_amount')
        return fields

class AccountTax(models.Model):
    _inherit = 'account.tax'
    
    @api.model
    def _load_pos_data_fields(self, config_id):
        """Add invoice_label and type_tax_use to POS loaded fields"""
        fields = super()._load_pos_data_fields(config_id)
        # Add invoice_label and type_tax_use if not already present
        if 'invoice_label' not in fields:
            fields.append('invoice_label')
        if 'type_tax_use' not in fields:
            fields.append('type_tax_use')
        return fields

class PosConfig(models.Model):
    _inherit = 'pos.config'

    receipt_logo = fields.Binary("Receipt Logo", help="Upload a custom logo to print on POS receipts.")
    company_name = fields.Char("Store Name", help="Add store name to display on receipt.")


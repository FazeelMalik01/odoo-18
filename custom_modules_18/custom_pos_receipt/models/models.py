# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PosConfig(models.Model):
    _inherit = 'pos.config'
    
    receipt_type = fields.Selection([
        ('doha', 'Doha Receipt'),
        ('icity', 'iCity Receipt')
    ], string='Receipt Type', help='Select the type of receipt format to use for this POS configuration',
       default='doha')
    receipt_logo = fields.Binary("Receipt Logo", help="Upload a custom logo to print on POS receipts.")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    pos_receipt_type = fields.Selection([
        ('doha', 'Doha Receipt'),
        ('icity', 'iCity Receipt')
    ], string='Receipt Type', help='Select the type of receipt format to use',
       config_parameter='custom_pos_receipt.pos_receipt_type')


class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    def get_custom_receipt_data(self):
        """Get formatted data for custom receipt"""
        self.ensure_one()
        return {
            'order': self,
            'lines': self.lines,
            'company': self.company_id,
            'cashier': self.user_id.name if self.user_id else False,
            'payments': self.statement_ids,
        }


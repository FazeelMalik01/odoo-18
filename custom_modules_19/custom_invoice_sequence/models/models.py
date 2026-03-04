from odoo import models

class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_next_sequence_format(self):
        """Override to ensure invoice sequence starts from custom values per company"""
        format_string, format_values = super()._get_next_sequence_format()
        
        # Company 1: start from 837
        if (self.move_type == 'out_invoice' and 
            self.company_id.id == 1 and 
            self.journal_id.type == 'sale'):
            
            current_seq = format_values.get('seq', 0)
            if current_seq < 837:
                format_values['seq'] = 836  # next will be 837
        
        # Company 2: start from 01577
        if (self.move_type == 'out_invoice' and 
            self.company_id.id == 2 and 
            self.journal_id.type == 'sale'):
            
            current_seq = format_values.get('seq', 0)
            if current_seq < 1577:
                format_values['seq'] = 1576  # next will be 1577
        
        return format_string, format_values

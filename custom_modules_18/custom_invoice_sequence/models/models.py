from odoo import models

class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_next_sequence_format(self):
        """Override to ensure invoice starts from 837 for Company 1"""
        format_string, format_values = super()._get_next_sequence_format()
        
        # Check if this is an invoice for company 1
        if (self.move_type == 'out_invoice' and 
            self.company_id.id == 1 and 
            self.journal_id.type == 'sale'):
            
            # Force minimum sequence to 837
            current_seq = format_values.get('seq', 0)
            if current_seq < 837:
                # Set to 836 so next increment will be 837
                format_values['seq'] = 836
        
        return format_string, format_values
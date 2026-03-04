from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Override inalterable_hash to make it editable
    inalterable_hash = fields.Char(string="Inalterability Hash", readonly=False, copy=False, index='btree_not_null')

    def write(self, vals):
        """
        Override write to allow clearing the inalterable_hash field.
        """
        # If we're clearing the hash (setting it to False or empty), allow it by temporarily removing it from vals
        # and clearing it directly after the write
        clearing_hash = 'inalterable_hash' in vals and not vals.get('inalterable_hash')
        
        if clearing_hash:
            # Remove hash from vals to bypass the validation check
            vals.pop('inalterable_hash')
            # Call super write without the hash field
            result = super().write(vals)
            # Now clear the hash directly using SQL to bypass the check
            if any(move.inalterable_hash for move in self):
                self._cr.execute(
                    "UPDATE account_move SET inalterable_hash = NULL WHERE id IN %s",
                    (tuple(self.ids),)
                )
                self.invalidate_recordset(['inalterable_hash'])
            return result
        
        return super().write(vals)

    def button_draft_clear_hash(self):
        """
        Custom method to clear the inalterable_hash and move to draft.
        This bypasses the normal restrictions by clearing the hash first.
        """
        if any(move.state not in ('cancel', 'posted') for move in self):
            raise UserError(_("Only posted/cancelled journal entries can be reset to draft."))
        if any(move.need_cancel_request for move in self):
            raise UserError(_("You can't reset to draft those journal entries. You need to request a cancellation instead."))
        
        # Clear the hash field directly using SQL to bypass validation
        moves_with_hash = self.filtered('inalterable_hash')
        if moves_with_hash:
            self.env.cr.execute(
                "UPDATE account_move SET inalterable_hash = NULL WHERE id IN %s",
                (tuple(moves_with_hash.ids),)
            )
            moves_with_hash.invalidate_recordset(['inalterable_hash'])
        
        # Now perform the standard draft operations
        # Remove analytics entries
        self.line_ids.analytic_line_ids.with_context(skip_analytic_sync=True).unlink()
        
        # Detach attachments
        self._detach_attachments()
        
        # Set to draft
        self.state = 'draft'
        self.sending_data = False


from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CommissionSlices(models.Model):
    _name = 'commission.slices'
    _description = 'Commission Plan'

    name = fields.Char(String='Name')
    slice_seq = fields.Integer(string='Slice Sequence', readonly=True)
    from_amount = fields.Float(string='From Amount', required=True, digits=(12, 2))
    to_amount = fields.Float(string='To Amount', required=True, digits=(12, 2))
    commission_percentage = fields.Float(string='Commission %', required=True, digits=(5, 2),
                                         help="Percentage commission for this slice")

    @api.model
    def create(self, vals):
        if 'slice_seq' not in vals or not vals['slice_seq']:
            last = self.search([], order="slice_seq desc", limit=1)
            vals['slice_seq'] = last.slice_seq + 1 if last else 1
        return super().create(vals)

    def unlink(self):
        result = super().unlink()
        self._resequence()
        return result

    @api.model
    def _resequence(self):
        all_slices = self.search([], order='slice_seq asc')
        for idx, rec in enumerate(all_slices, start=1):
            rec.slice_seq = idx

    @api.constrains('from_amount', 'to_amount')
    def _check_overlap(self):
        for rec in self:
            if rec.from_amount >= rec.to_amount:
                raise ValidationError("From Amount must be less than To Amount.")

            overlap = self.search([
                ('id', '!=', rec.id),
                '|',
                '&', ('from_amount', '<', rec.to_amount), ('to_amount', '>', rec.from_amount),
                '&', ('from_amount', '<', rec.to_amount), ('to_amount', '=', False)
            ])
            if overlap:
                raise ValidationError("Amount range overlaps with another commission slice.")

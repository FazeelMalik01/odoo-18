from odoo import models, fields, api
from datetime import timedelta

class FreezeMembershipWizard(models.TransientModel):
    _name = 'freeze.membership.wizard'
    _description = 'Freeze Membership Wizard'

    membership_id = fields.Many2one('memberships.member', string='Membership')
    duration_days = fields.Integer(string='Duration (Days)', required=True)
    extra_charges = fields.Monetary(string='Extra Charges')
    currency_id = fields.Many2one('res.currency', related='membership_id.currency_id')

    def action_confirm(self):
        self.ensure_one()
        membership = self.membership_id

        # Calculate extended end date based on current end_date + wizard duration
        extended_date = False
        if membership.end_date and self.duration_days:
            extended_date = membership.end_date + timedelta(days=self.duration_days)

        membership.write({
            'freeze': True,
            'freeze_duration_days': self.duration_days,
            'freeze_extra_charges': self.extra_charges,
        })

        self.env['freeze.membership.log'].create({
            'membership_id': membership.id,
            'duration_days': self.duration_days,
            'extra_charges': self.extra_charges,
            'freeze_date': fields.Date.today(),
            'extended_end_date': extended_date,
        })

        # Create separate invoice for extra charges if any
        if self.extra_charges and self.extra_charges > 0:
            invoice_line = [(0, 0, {
                'name': f'Freeze Extra Charges - {membership.gym_membership_number}',
                'quantity': 1,
                'price_unit': self.extra_charges,
            })]
            invoice = self.env['account.move'].sudo().create({
                'partner_id': membership.gym_member_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': invoice_line,
                'move_type': 'out_invoice',
                'memberships_member_id': membership.id,  # links to same membership
            })
            invoice.action_post() 
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """Cancel — just close wizard, freeze stays False"""
        return {'type': 'ir.actions.act_window_close'}
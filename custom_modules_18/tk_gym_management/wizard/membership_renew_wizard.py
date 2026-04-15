# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, models, fields, _


class MembershipRenewWizard(models.TransientModel):
    """Membership Renew Wizard"""
    _name = "membership.renew.wizard"
    _description = __doc__

    member_id = fields.Many2one("res.partner", domain=[('is_member', '=', True)],
                                required=True)
    membership_type_id = fields.Many2one('product.template',
                                         domain=[('is_membership', '=', True)], required=True)
    duration_id = fields.Many2one("membership.duration",
                                  related="membership_type_id.membership_duration_id")
    start_date = fields.Date(required=True)
    end_date = fields.Date(compute='_compute_expiry_date_count')

    @api.model
    def default_get(self, fields_list):
        """default get"""
        res = super().default_get(fields_list)
        active_id = self._context.get('active_id')
        if active_id:
            member_id = self.env['memberships.member'].browse(active_id)
            res['member_id'] = member_id.gym_member_id.id
            res['membership_type_id'] = member_id.gym_membership_type_id.id
            res['start_date'] = member_id.end_date + timedelta(days=1)
        return res

    @api.depends('start_date', 'duration_id')
    def _compute_expiry_date_count(self):
        """expiry date count"""
        end_date = fields.date.today()
        for rec in self:
            if rec.start_date:
                end_date = rec.start_date + relativedelta(months=rec.duration_id.duration)
            rec.end_date = end_date

    def renew_membership(self):
        """renew membership"""
        active_id = self._context.get('active_id')
        if active_id:
            membership_id = self.env['memberships.member'].browse(active_id)
            if (membership_id.invoice_membership_id
                    and membership_id.invoice_membership_id.status_in_payment != 'paid'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Warning"),
                        'type': 'warning',
                        'message': _(
                            "Please pay the previous membership invoice before renewing your "
                            "membership."),
                    }
                }
            data = {
                'gym_member_id': self.member_id.id,
                'gym_membership_type_id': self.membership_type_id.id,
                'start_date': self.start_date,
                'renewed_from': membership_id.id,
                'duration_id': self.duration_id.id,
                'price': self.membership_type_id.list_price
            }
            new_membership_id = self.env['memberships.member'].create(data)
            membership_id.write({
                'renewed': True,
                'renewed_membership': new_membership_id.id,
                'stages': 'close'
            })
            return {
                'type': "ir.actions.act_window",
                'name': 'Renewed Membership',
                'res_model': 'memberships.member',
                'res_id': new_membership_id.id,
                'view_mode': 'form',
                'target': 'current'
            }

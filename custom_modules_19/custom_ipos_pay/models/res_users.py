# -*- coding: utf-8 -*-

from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def write(self, vals):
        res = super().write(vals)
        if (
            'company_id' in vals
            and self.env.uid in self.ids
            and not self.env.user.share
        ):
            self.env['payment.provider'].sudo().search(
                [('code', '=', 'ipos_pay')]
            )._ipos_sync_company_from_user_context()
        return res

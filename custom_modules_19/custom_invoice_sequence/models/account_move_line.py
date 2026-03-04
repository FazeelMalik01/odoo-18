from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            account_id = vals.get('account_id')
            partner_id = vals.get('partner_id')

            if account_id and partner_id:
                account = self.env['account.account'].browse(account_id)

                if account.account_type == 'liability_payable':
                    # Only set if empty to avoid overwriting manual labels
                    if not vals.get('name'):
                        partner = self.env['res.partner'].browse(partner_id)
                        vals['name'] = partner.name

        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)

        for line in self:
            if (
                line.account_id.account_type == 'liability_payable'
                and line.partner_id
                and line.name != line.partner_id.name
            ):
                # Bypass our override to avoid recursion
                super(AccountMoveLine, line).write({
                    'name': line.partner_id.name
                })

        return res
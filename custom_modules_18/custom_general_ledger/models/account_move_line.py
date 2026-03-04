# models/account_move_line.py
# from dataclasses import fields

from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    project_id = fields.Many2one(
        "project.project",
        string="Project",
        help="Related Project for this journal item"
    )

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        for move in self:
            if move.project_id:
                move.line_ids.write({"project_id": move.project_id.id})
        return res

    @api.model
    def get_general_ledger_data(self, project_id=None, partner_id=None):
        domain = []

        if project_id:
            domain.append(('project_id', '=', project_id))
        if partner_id:
            domain.append(('partner_id', '=', partner_id))

        records = self.search(domain, limit=50, order="date asc, id asc")

        running_balance = 0
        data = []

        for rec in records:
            running_balance += rec.debit - rec.credit
            data.append({
                'id': rec.id,
                'date': rec.date.strftime("%m/%d/%Y") if rec.date else "",
                'communication': rec.ref or rec.name or "",
                'partner': rec.partner_id.display_name or "",
                'debit': rec.debit,
                'credit': rec.credit,
                'balance': running_balance,
            })

        return data


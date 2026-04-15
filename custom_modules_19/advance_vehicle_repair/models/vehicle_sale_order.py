from odoo import models, fields, api, _

class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    jobcard_id = fields.Many2one('vehicle.jobcard', string='Job Card')

    def action_confirm(self):
        res = super().action_confirm()

        for order in self:
            if order.jobcard_id:
                order.jobcard_id.state = "confirmed"

        return res
    
    def action_open_jobcard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Job Card',
            'res_model': 'vehicle.jobcard',
            'view_mode': 'form',
            'res_id': self.jobcard_id.id,
            'target': 'current',
        }

class AccountMove(models.Model):
    _inherit = "account.move"

    jobcard_id = fields.Many2one(
        "vehicle.jobcard",
        string="Job Card",
        compute="_compute_jobcard_id",
        store=True,
    )

    @api.depends("invoice_line_ids.sale_line_ids.order_id.jobcard_id")
    def _compute_jobcard_id(self):
        for move in self:
            jobcard = False
            for line in move.invoice_line_ids:
                for sale_line in line.sale_line_ids:
                    if sale_line.order_id.jobcard_id:
                        jobcard = sale_line.order_id.jobcard_id
                        break
                if jobcard:
                    break
            move.jobcard_id = jobcard
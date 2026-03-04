from odoo import models, fields, api

class AnalyticPoLine(models.Model):
    _name = 'analytic.po.line'
    _description = 'PO User Lines'
    _rec_name = 'po_text'

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='cascade')
    po_text = fields.Char(string='Add Purchase Orders')

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    po_line_ids = fields.One2many('analytic.po.line', 'analytic_account_id', string='PO User Lines')

class AccountMove(models.Model):
    _inherit = 'account.move'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='المشاريع'
    )
    analytic_po_line_id = fields.Many2one(
        'analytic.po.line',
        string='Purchase Orders',
        domain="[('analytic_account_id', '=', analytic_account_id)]"
    )

    @api.model
    def get_purchase_orders(self):
        """
        Return all analytic.po.line records (po_text) for the frontend dropdown.
        """
        PoLine = self.env['analytic.po.line']
        po_lines = PoLine.search([], order='id desc')  # adjust domain/order as needed

        result = []
        for pl in po_lines:
            result.append({
                'id': pl.id,
                # use po_text as the label shown in dropdown
                'name': pl.po_text or f'PO_LINE-{pl.id}',
                # include analytic account name if present
                'analytic_account_name': pl.analytic_account_id.name if pl.analytic_account_id else '',
            })
        return result

    
    @api.onchange('analytic_account_id')
    def _onchange_analytic_account_id_lines(self):
        """When analytic account is selected in invoice header,
        apply it to all invoice lines' analytic_distribution."""
        for move in self:
            if move.invoice_line_ids and move.analytic_account_id:
                for line in move.invoice_line_ids:
                    line.analytic_distribution = {
                        move.analytic_account_id.id: 100.0
                    }
            elif move.invoice_line_ids:
                for line in move.invoice_line_ids:
                    line.analytic_distribution = {}
    
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    analytic_po_line_id = fields.Many2one(
        'analytic.po.line',
        string='Purchase Orders',
    )

    @api.onchange('product_id')
    def _onchange_product_set_analytic(self):
        """Auto-assign analytic fields when a product is selected."""
        move = self.move_id
        if move:
            # Assign analytic distribution from invoice header
            if move.analytic_account_id:
                self.analytic_distribution = {
                    move.analytic_account_id.id: 100.0
                }

            # Assign PO Line from invoice header
            if move.analytic_po_line_id:
                self.analytic_po_line_id = move.analytic_po_line_id
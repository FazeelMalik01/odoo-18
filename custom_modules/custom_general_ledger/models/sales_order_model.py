from odoo import fields, models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    vendor_id = fields.Many2one(
        "res.partner",
        string="Vendor",  # Only vendors
        help="Select the vendor for this sales order."
    )

    project_id = fields.Many2one(
        "project.project",
        string="Project",
        help="Project related to this Sale Order"
    )

    def _prepare_invoice(self):
        """Extend invoice values with vendor and project from sale order"""
        invoice_vals = super()._prepare_invoice()
        invoice_vals.update({
            "vendor_id": self.vendor_id.id,
            "project_id": self.project_id.id,
        })
        return invoice_vals

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_invoice_line(self, **optional_values):
        """Pass project_id down to invoice lines (account.move.line)."""
        res = super()._prepare_invoice_line(**optional_values)
        if self.order_id.project_id:
            res["project_id"] = self.order_id.project_id.id
        return res
from odoo import models, fields, api, _
from odoo.tools import float_compare


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    # stored so read_group can sum it
    inward_quantity = fields.Float(
        string="Balance",
        compute="_compute_inward_quantity",
        store=True,
        digits="Product Unit of Measure",
    )

    @api.depends("qty_done", "quantity", "location_id.usage", "location_dest_id.usage")
    def _compute_inward_quantity(self):
        """
        Compute net inward movement:
        + qty_done for inbound (external → internal/transit)
        - qty_done for outbound (internal/transit → external)
        0 for internal ↔ internal or external ↔ external
        """
        for rec in self:
            # Use qty_done if available, otherwise fall back to quantity
            qty = rec.qty_done if rec.qty_done is not None else (rec.quantity or 0.0)

            # Inbound: outside → inside
            if (
                rec.location_id.usage not in ("internal", "transit")
                and rec.location_dest_id.usage in ("internal", "transit")
            ):
                rec.inward_quantity = qty

            # Outbound: inside → outside
            elif (
                rec.location_id.usage in ("internal", "transit")
                and rec.location_dest_id.usage not in ("internal", "transit")
            ):
                rec.inward_quantity = -qty

            # Internal transfer or others
            else:
                rec.inward_quantity = 0.0

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        """
        Aggregate 'quantity' field as net sum of inward quantities.
        """
        result = super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)

        if "quantity" in fields:
            for group in result:
                sub_domain = group.get("__domain", domain)
                data = self.env["stock.move.line"].search(sub_domain)
                # Calculate actual sum dynamically
                net_qty = sum(data.mapped("inward_quantity"))
                group["quantity"] = net_qty
        return result
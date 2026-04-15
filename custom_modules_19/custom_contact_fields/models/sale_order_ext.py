from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    po_number = fields.Char(string="PO Number", copy=False)

    def _prepare_invoice(self):
        """Extend to propagate PO Number to the generated customer invoice."""
        self.ensure_one()
        values = super()._prepare_invoice()
        if self.po_number:
            values['po_number'] = self.po_number
        return values

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    dropship_vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        readonly=True,
        copy=False,
    )

    # Independent per-line warehouse selector.
    # It defaults from the order's warehouse but can then be changed per line
    # without impacting other lines.
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string="Warehouse",
        domain="[('company_id', '=', company_id)]",
        readonly=False,
    )

    @api.onchange('order_id')
    def _onchange_order_id_set_warehouse(self):
        """When a line is attached to an order, pre-fill its warehouse from the order."""
        for line in self:
            if line.order_id and not line.warehouse_id:
                line.warehouse_id = line.order_id.warehouse_id

    @api.onchange('product_id')
    def _onchange_product_set_default_warehouse(self):
        for line in self:
            if line.product_id:
                default_wh = line.product_id.product_tmpl_id.default_warehouse_id
                if default_wh:
                    line.warehouse_id = default_wh

    def _prepare_procurement_values(self):
        """Inject per-line warehouse into procurement values so deliveries split by warehouse.

        Core `sale_stock` uses this dict to determine which warehouse / picking type to use.
        By overriding the `warehouse_id` here to prefer the line's warehouse, stock moves
        and pickings will be created per warehouse instead of only per order.
        """
        self.ensure_one()
        values = super()._prepare_procurement_values()
        warehouse = self.warehouse_id or self.order_id.warehouse_id
        if warehouse:
            values['warehouse_id'] = warehouse
        return values

class AccountMove(models.Model):
    _inherit = 'account.move'

    order_id = fields.Char(
        string="Order ID",
        copy=False,
    )

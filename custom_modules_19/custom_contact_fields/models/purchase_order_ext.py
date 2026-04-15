from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Independent warehouse per PO line
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string="Warehouse",
        domain="[('company_id', '=', company_id)]",
    )

    dropship_customer_id = fields.Many2one(
        'res.partner',
        string="Customer",
        domain="[('customer_rank', '>', 0)]",
        help="Customer to which this dropship line will be delivered.",
    )

    @api.onchange('order_id')
    def _onchange_order_id_set_warehouse(self):
        """Default warehouse from the purchase order."""
        for line in self:
            if line.order_id and not line.warehouse_id:
                line.warehouse_id = line.order_id.picking_type_id.warehouse_id

    @api.onchange('product_id')
    def _onchange_product_set_default_warehouse(self):
        for line in self:
            if line.product_id:
                default_wh = line.product_id.product_tmpl_id.default_warehouse_id
                if default_wh:
                    line.warehouse_id = default_wh

    def _prepare_stock_moves(self, picking):
        """Inject warehouse into stock moves so receipts split by warehouse.

        If dropshipping is enabled on the line, we skip stock moves so no delivery/receipt is created for it.
        """
        if self.dropshipping:
            return []

        moves = super()._prepare_stock_moves(picking)

        warehouse = self.warehouse_id or self.order_id.picking_type_id.warehouse_id

        if warehouse:
            for move in moves:
                move['warehouse_id'] = warehouse.id
                move['location_dest_id'] = warehouse.lot_stock_id.id

        return moves

    dropshipping = fields.Boolean(string="Dropshipping")
    dropship_sale_line_id = fields.Many2one(
        'sale.order.line',
        string='Dropship Sale Order Line',
        readonly=True,
        copy=False,
    )


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    amount_untaxed = fields.Monetary(string="Subtotal")

    dropship_sale_order_id = fields.Many2one(
        'sale.order',
        string='Dropship Sale Order',
        readonly=True,
        copy=False,
    )

    def action_view_dropship_sale_order(self):
        self.ensure_one()
        if not self.dropship_sale_order_id:
            return False

        action = self.env.ref('sale.action_orders').read()[0]
        sale_order = self.dropship_sale_order_id
        action.update({
            'view_mode': 'form',
            'views': [(self.env.ref('sale.view_order_form').id, 'form')],
            'res_id': sale_order.id,
            'domain': [('id', '=', sale_order.id)],
        })
        return action

    def button_confirm(self):
        res = super().button_confirm()
        for order in self:
            dropship_lines = order.order_line.filtered(lambda l: l.dropshipping and l.product_id and not l.dropship_sale_line_id)
            if not dropship_lines:
                continue

            sale_order = order.dropship_sale_order_id
            if not sale_order:
                customer = order.dest_address_id or order.company_id.partner_id
                sale_order = self.env['sale.order'].sudo().create({
                    'partner_id': customer.id,
                    'origin': order.name,
                    'company_id': order.company_id.id,
                })
                order.sudo().write({'dropship_sale_order_id': sale_order.id})

            for line in dropship_lines:
                sol = self.env['sale.order.line'].sudo().create({
                    'order_id': sale_order.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_qty,
                    'product_uom_id': line.product_uom_id.id,
                    'price_unit': line.price_unit,
                    'name': line.name or line.product_id.display_name,
                    'dropship_vendor_id': order.partner_id.id,
                })
                line.sudo().write({'dropship_sale_line_id': sol.id})

        return res
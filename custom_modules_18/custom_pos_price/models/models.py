from odoo import models, api, _, fields
from odoo.exceptions import UserError

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.model
    def get_existing_lots(self, company_id, product_id):
        # Call super if you want original behavior first
        # original_lots = super().get_existing_lots(company_id, product_id)

        self.check_access('read')
        pos_config = self.env['pos.config'].browse(self._context.get('config_id'))
        if not pos_config:
            raise UserError(_('No PoS configuration found'))

        src_loc = pos_config.picking_type_id.default_location_src_id

        domain = [
            '|',
            ('company_id', '=', False),
            ('company_id', '=', company_id),
            ('product_id', '=', product_id),
            ('location_id', 'in', src_loc.child_internal_location_ids.ids),
            ('quantity', '>', 0),
            ('lot_id', '!=', False),
        ]

        groups = self.sudo().env['stock.quant']._read_group(
            domain=domain,
            groupby=['lot_id'],
            aggregates=['quantity:sum']
        )

        # Get product information for fallback price
        product = self.env['product.product'].browse(product_id)
        product_sale_price = product.list_price

        result = []
        for lot_recordset, total_quantity in groups:
            if lot_recordset:
                # Use lot's my_price if it's greater than 0, otherwise use product's sale price
                lot_price = lot_recordset.my_price if lot_recordset.my_price > 0 else product_sale_price
                
                result.append({
                    'id': lot_recordset.id,
                    'name': lot_recordset.name,
                    'product_qty': total_quantity,
                    'cost_price': lot_price
                })

        # You can also modify or add extra logic here if needed
        return result


class StockLot(models.Model):
    _inherit = "stock.lot"

    my_price = fields.Float(string="My Price", help="Custom POS Sale Price for this lot/serial")


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    serial = fields.Many2one(
        "stock.lot",
        string="Serial",
        domain="[('product_id', '=', product_id), ('quant_ids.quantity', '>', 0)]",
    )

    @api.onchange("product_id")
    def _onchange_product_id_tracking(self):
        """When product changes:
        - Only show lots with stock available
        """
        domain = []
        if self.product_id and self.product_id.tracking == "lot":
            domain = [
                ("product_id", "=", self.product_id.id),
                ("quant_ids.quantity", ">", 0),   # ✅ only lots with stock
            ]
        else:
            self.serial = False
        return {"domain": {"serial": domain}}

    @api.onchange("serial")
    def _onchange_serial_set_price(self):
        """If product is lot-tracked and a serial is selected, set price from serial.my_price."""
        if not self.serial or not self.product_id:
            return
        # Only apply for lot-tracked products and matching product on the lot
        if self.product_id.tracking == "lot" and (not self.serial.product_id or self.serial.product_id == self.product_id):
            # Use lot's my_price if it's greater than 0, otherwise use product's sale price
            lot_price = self.serial.my_price if self.serial.my_price > 0 else self.product_id.list_price
            self.price_unit = lot_price


class StockMove(models.Model):
    _inherit = "stock.move"

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)

        # if SO line has a serial selected
        if self.sale_line_id and self.sale_line_id.serial:
            lot = self.sale_line_id.serial
            vals["lot_id"] = lot.id

            # find quant for lot → set correct location
            quant = self.env["stock.quant"].search([
                ("lot_id", "=", lot.id),
                ("product_id", "=", self.product_id.id),
                ("quantity", ">", 0)
            ], limit=1)
            if quant:
                vals["location_id"] = quant.location_id.id

        return vals

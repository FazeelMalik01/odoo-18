# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    has_move_lines_with_owner = fields.Boolean(
        string='Has Move Lines with Owner',
        compute='_compute_has_move_lines_with_owner',
        help='True if this picking has move lines with owner (consignment products)'
    )

    @api.depends('move_line_ids', 'move_line_ids.owner_id', 'move_line_ids.quantity')
    def _compute_has_move_lines_with_owner(self):
        """Compute if picking has move lines with owner"""
        for picking in self:
            picking.has_move_lines_with_owner = bool(
                picking.move_line_ids.filtered(
                    lambda ml: ml.owner_id and ml.product_id and ml.quantity > 0
                )
            )

    def action_create_vendor_bill_from_picking(self):
        """Create vendor bill(s) for all move lines in this picking that have owners"""
        self.ensure_one()

        if self.state != 'done':
            raise UserError('Vendor bills can only be created for completed transfers.')

        if self.picking_type_code != 'outgoing':
            raise UserError('Vendor bills can only be created for outgoing deliveries.')

        # Get all move lines with owners
        move_lines_with_owner = self.move_line_ids.filtered(
            lambda ml: ml.owner_id and ml.product_id and ml.quantity > 0)

        if not move_lines_with_owner:
            raise UserError(
                'No move lines with owner found in this transfer. Vendor bills can only be created for consignment products with owners.')

        # Group by owner to create one bill per owner
        owner_dict = {}
        for line in move_lines_with_owner:
            owner_id = line.owner_id.id
            if owner_id not in owner_dict:
                owner_dict[owner_id] = {
                    'partner_id': line.owner_id.id,
                    'lines': []
                }
            owner_dict[owner_id]['lines'].append(line)

        # Create vendor bills
        bills = []
        for owner_id, owner_data in owner_dict.items():
            # Get product accounts (use first product's account as base)
            first_line = owner_data['lines'][0]
            product_accounts = first_line.product_id.product_tmpl_id.get_product_accounts()
            expense_account = product_accounts.get('expense')

            if not expense_account:
                raise UserError(f'Please configure an expense account for product {first_line.product_id.name}.')

            # Get the default purchase journal
            journal = self.env['account.journal'].search([
                ('type', '=', 'purchase'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)

            if not journal:
                raise UserError('Please configure a purchase journal.')

            # Create invoice lines
            invoice_lines = []
            for line in owner_data['lines']:
                invoice_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'price_unit': 0.0,  # Can be updated manually
                    'account_id': expense_account.id,
                    'name': f"{line.product_id.name} (Consignment - {self.name})",
                    'product_uom_id': line.product_uom_id.id if line.product_uom_id else line.product_id.uom_id.id,
                }))

            # Create vendor bill
            bill_vals = {
                'partner_id': owner_data['partner_id'],
                'move_type': 'in_invoice',
                'journal_id': journal.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': invoice_lines,
            }

            bill = self.env['account.move'].create(bill_vals)
            bills.append(bill)

        # Return action to open the first bill (or list view if multiple)
        if len(bills) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Vendor Bill',
                'res_model': 'account.move',
                'res_id': bills[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Vendor Bills',
                'res_model': 'account.move',
                'domain': [('id', 'in', [b.id for b in bills])],
                'view_mode': 'list,form',
                'target': 'current',
            }


class ConsignmentReport(models.Model):
    _name = 'consignment.report'
    _description = 'Consignment Report'
    _order = 'create_date desc'

    name = fields.Char(string='Name', compute='_compute_name', store=True, readonly=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True)
    from_date = fields.Date(string='From Date', required=True)
    to_date = fields.Date(string='To Date', required=True)
    product_line_ids = fields.One2many('consignment.report.line', 'consignment_report_id', string='Products', readonly=True)
    total_quantity = fields.Float(string='Total Quantity', compute='_compute_total_quantity', store=True, readonly=True)
    vendor_bill_id = fields.Many2one('account.move', string='Vendor Bill', readonly=True, copy=False)
    has_vendor_bill = fields.Boolean(string='Has Vendor Bill', compute='_compute_has_vendor_bill', store=True)

    @api.depends('vendor_id', 'from_date', 'to_date')
    def _compute_name(self):
        for record in self:
            if record.vendor_id and record.from_date and record.to_date:
                record.name = f"{record.vendor_id.name} - {record.from_date} to {record.to_date}"
            else:
                record.name = "New"

    @api.depends('product_line_ids', 'product_line_ids.quantity')
    def _compute_total_quantity(self):
        for record in self:
            record.total_quantity = sum(record.product_line_ids.mapped('quantity'))
    
    @api.depends('vendor_bill_id')
    def _compute_has_vendor_bill(self):
        for record in self:
            record.has_vendor_bill = bool(record.vendor_bill_id)

    @api.onchange('vendor_id', 'from_date', 'to_date')
    def _onchange_dates(self):
        """Validate date range when vendor or dates change"""
        if self.vendor_id and self.from_date and self.to_date:
            if self.to_date < self.from_date:
                return {
                    'warning': {
                        'title': 'Invalid Date Range',
                        'message': 'To Date must be greater than or equal to From Date',
                    }
                }
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to update product lines after record is created"""
        records = super(ConsignmentReport, self).create(vals_list)
        for record in records:
            if record.vendor_id and record.from_date and record.to_date:
                record._update_product_lines()
        return records
    
    def write(self, vals):
        """Override write to update product lines when vendor or dates change"""
        result = super().write(vals)
        for record in self:
            # Check if vendor, from_date, or to_date were updated
            if any(field in vals for field in ['vendor_id', 'from_date', 'to_date']):
                if record.vendor_id and record.from_date and record.to_date:
                    record._update_product_lines()
        return result

    def _update_product_lines(self):
        """Update product lines based on vendor and date range (separate IN / OUT per product)"""
        self.ensure_one()

        # Clear existing lines
        self.product_line_ids.unlink()

        domain = [
            ('state', '=', 'done'),
            ('scheduled_date', '>=', self.from_date),
            ('scheduled_date', '<=', self.to_date),
            '|',
                '&',
                    ('picking_type_code', '=', 'outgoing'),
                    ('location_dest_id.usage', '=', 'customer'),
                '&',
                    ('picking_type_code', '=', 'incoming'),
                    ('location_id.usage', '=', 'customer'),
        ]

        pickings = self.env['stock.picking'].search(domain)
        moves = pickings.mapped('move_ids_without_package')

        moves_with_owner = moves.filtered(
            lambda m: any(
                ml.owner_id and ml.owner_id.id == self.vendor_id.id
                for ml in m.move_line_ids
            )
        )

        # --------------------------------------------------
        # Accumulator: ONE entry per (product, direction)
        # --------------------------------------------------
        product_qty_map = {}

        for move in moves_with_owner:

            # Determine direction
            if move.location_dest_id.usage == 'customer':
                sign = 1
                direction = 'out'
            elif move.location_id.usage == 'customer':
                sign = -1
                direction = 'in'
            else:
                continue

            move_lines = move.move_line_ids.filtered(
                lambda ml: ml.owner_id
                and ml.owner_id.id == self.vendor_id.id
                and ml.quantity > 0
            )

            for ml in move_lines:
                product = ml.product_id
                if not product:
                    continue

                key = (product.id, direction)
                qty = sign * ml.quantity

                if key not in product_qty_map:
                    product_qty_map[key] = {
                        'product_id': product.id,
                        'direction': direction,
                        'quantity': 0.0,
                        'uom_id': (
                            ml.product_uom_id.id
                            if ml.product_uom_id
                            else product.uom_id.id
                        ),
                    }

                product_qty_map[key]['quantity'] += qty

        # --------------------------------------------------
        # Create report lines
        # --------------------------------------------------
        for data in product_qty_map.values():

            if not data['quantity']:
                continue

            self.env['consignment.report.line'].create({
                'consignment_report_id': self.id,
                'product_id': data['product_id'],
                'quantity': data['quantity'],
                'uom_id': data['uom_id']
            })

    def action_create_vendor_bill(self):
        """Create vendor bill for the products in this consignment report"""
        self.ensure_one()

        if not self.vendor_id:
            raise UserError('Vendor is required to create a vendor bill.')

        if not self.product_line_ids:
            raise UserError('No products found for this date range. Cannot create vendor bill.')

        # Get the default purchase journal
        journal = self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not journal:
            raise UserError('Please configure a purchase journal.')

        # Create invoice lines
        invoice_lines = []
        for line in self.product_line_ids:
            product_accounts = line.product_id.product_tmpl_id.get_product_accounts()
            expense_account = product_accounts.get('expense')

            if not expense_account:
                raise UserError(f'Please configure an expense account for product {line.product_id.name}.')

            # Get product list price
            price_unit = line.product_id.list_price or 0.0

            invoice_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'price_unit': price_unit,
                'account_id': expense_account.id,
                'name': line.product_id.name,
                'product_uom_id': line.uom_id.id,
            }))

        # Create vendor bill
        bill_vals = {
            'partner_id': self.vendor_id.id,
            'move_type': 'in_invoice',
            'journal_id': journal.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
        }

        bill = self.env['account.move'].create(bill_vals)
        
        # Store the vendor bill reference
        self.write({'vendor_bill_id': bill.id})

        # Return action to open the created bill
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Bill',
            'res_model': 'account.move',
            'res_id': bill.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_vendor_bill(self):
        """Open the vendor bill associated with this consignment report"""
        self.ensure_one()
        
        if not self.vendor_bill_id:
            raise UserError('No vendor bill has been created for this consignment report.')
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Bill',
            'res_model': 'account.move',
            'res_id': self.vendor_bill_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ConsignmentReportLine(models.Model):
    _name = 'consignment.report.line'
    _description = 'Consignment Report Line'

    consignment_report_id = fields.Many2one('consignment.report', string='Consignment Report', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)

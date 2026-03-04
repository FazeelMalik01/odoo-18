# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime


class CustomCostAdjustmentLine(models.Model):
    _name = 'custom_cost_adjustment.line'
    _description = 'Custom Cost Adjustment Line'

    adjustment_id = fields.Many2one('custom_cost_adjustment.custom_cost_adjustment', string='Cost Adjustment', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    qty = fields.Float(string='Quantity', required=True, readonly=True)
    cost_price = fields.Float(string='Cost Price', required=True)
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost', store=True)
    cost_after_adjustment = fields.Float(string='Cost After Adjustment', required=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Automatically set cost price and quantity when product is selected"""
        if self.product_id:
            # Get the standard price (cost) of the product
            cost = self.product_id.standard_price
            self.cost_price = cost
            # Also update cost_after_adjustment with the same value initially
            if not self.cost_after_adjustment or self.cost_after_adjustment == 0:
                self.cost_after_adjustment = cost
            # Auto-populate quantity from stock.change.product.qty
            self._update_qty_from_stock_change()
    
    def _update_qty_from_stock_change(self):
        """Update quantity from stock.change.product.qty model"""
        if self.product_id:
            # Find the most recent stock change for this product
            stock_change = self.env['stock.change.product.qty'].search([
                ('product_id', '=', self.product_id.id)
            ], order='create_date desc', limit=1)
            if stock_change and stock_change.new_quantity:
                self.qty = stock_change.new_quantity
            else:
                # Fallback to product's current quantity on hand
                self.qty = self.product_id.qty_available or 0.0

    @api.onchange('qty', 'cost_price')
    def _onchange_qty_cost_price(self):
        """Update cost_after_adjustment when qty or cost_price changes"""
        # Trigger parent totals recalculation
        if self.adjustment_id:
            # Recalculate totals for the parent
            self.adjustment_id._compute_totals()
            # Update this line's cost_after_adjustment
            if self.adjustment_id.average_cost > 0:
                self.cost_after_adjustment = self.adjustment_id.average_cost

    @api.depends('qty', 'cost_price')
    def _compute_total_cost(self):
        """Compute total cost as qty × cost_price"""
        for line in self:
            line.total_cost = line.qty * line.cost_price

    def write(self, vals):
        """Override write to prevent editing when parent is posted and update cost_after_adjustment when qty or cost_price changes"""
        for line in self:
            # Allow automatic updates (from context) even if posted
            if line.adjustment_id and line.adjustment_id.date_posted and not self.env.context.get('skip_posted_check'):
                # Only block manual edits, allow automatic updates
                if not self.env.context.get('auto_update'):
                    raise UserError('You cannot edit lines of a posted cost adjustment.')
        result = super().write(vals)
        # Skip update if we're already updating from totals computation
        if not self.env.context.get('skip_update'):
            if 'qty' in vals or 'cost_price' in vals:
                for line in self:
                    if line.adjustment_id:
                        # Trigger recomputation of totals which will update all lines
                        line.adjustment_id._compute_totals()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to prevent creating lines when parent is posted and update cost_after_adjustment after creation"""
        # Check if any parent is posted
        for vals in vals_list:
            if vals.get('adjustment_id'):
                adjustment = self.env['custom_cost_adjustment.custom_cost_adjustment'].browse(vals['adjustment_id'])
                if adjustment.date_posted and not self.env.context.get('skip_posted_check'):
                    raise UserError('You cannot add lines to a posted cost adjustment.')
            # Auto-populate qty and cost_price if product_id is provided
            if vals.get('product_id'):
                product = self.env['product.product'].browse(vals['product_id'])
                # Set cost_price if not provided
                if 'cost_price' not in vals or not vals.get('cost_price'):
                    vals['cost_price'] = product.standard_price or 0.0
                # Set cost_after_adjustment if not provided
                if 'cost_after_adjustment' not in vals or not vals.get('cost_after_adjustment'):
                    vals['cost_after_adjustment'] = product.standard_price or 0.0
                # Auto-populate qty if not provided
                if 'qty' not in vals or not vals.get('qty'):
                    stock_change = self.env['stock.change.product.qty'].search([
                        ('product_id', '=', product.id)
                    ], order='create_date desc', limit=1)
                    if stock_change and stock_change.new_quantity:
                        vals['qty'] = stock_change.new_quantity
                    else:
                        vals['qty'] = product.qty_available or 0.0
        lines = super().create(vals_list)
        for line in lines:
            if line.adjustment_id:
                # Trigger recomputation of totals which will update all lines
                line.adjustment_id._compute_totals()
        return lines

    def action_open_product_template(self):
        """Open the product template form view"""
        self.ensure_one()
        if not self.product_id:
            return False
        # Get the product template
        product_template = self.product_id.product_tmpl_id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Product',
            'res_model': 'product.template',
            'res_id': product_template.id,
            'view_mode': 'form',
            'view_id': self.env.ref('product.product_template_only_form_view').id,
            'target': 'current',
        }


class CustomCostAdjustment(models.Model):
    _name = 'custom_cost_adjustment.custom_cost_adjustment'
    _description = 'Custom Cost Adjustment'

    name = fields.Char(string='Name', required=True)
    
    @api.model
    def _default_name(self):
        """Generate a default name for the cost adjustment"""
        return self.env['ir.sequence'].next_by_code('custom_cost_adjustment') or 'New'
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set default name if not provided"""
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self._default_name()
        return super().create(vals_list)
    
    date_posted = fields.Datetime(string='Posted Date', readonly=True)
    status = fields.Char(string='Status', compute='_compute_status', store=False)
    posted_label = fields.Char(string='Posted Label', compute='_compute_posted_label', store=False)
    optional_note = fields.Text(string='Optional Note')
    
    @api.depends('date_posted')
    def _compute_status(self):
        """Compute status based on date_posted"""
        for adjustment in self:
            adjustment.status = 'Posted' if adjustment.date_posted else 'Not Posted'
    
    @api.depends('date_posted')
    def _compute_posted_label(self):
        """Compute posted label for header"""
        for adjustment in self:
            adjustment.posted_label = 'POSTED' if adjustment.date_posted else ''
    line_ids = fields.One2many('custom_cost_adjustment.line', 'adjustment_id', string='Adjustment Lines')
    total_qty = fields.Float(string='Total Quantity', compute='_compute_totals', store=True)
    total_cost_sum = fields.Float(string='Total Cost Sum', compute='_compute_totals', store=True)
    average_cost = fields.Float(string='Average Cost', compute='_compute_totals', store=True)

    @api.depends('line_ids.qty', 'line_ids.total_cost')
    def _compute_totals(self):
        """Compute total quantity, total cost sum, and average cost, then update all lines"""
        for adjustment in self:
            total_qty = sum(adjustment.line_ids.mapped('qty'))
            total_cost_sum = sum(adjustment.line_ids.mapped('total_cost'))
            average_cost = total_cost_sum / total_qty if total_qty > 0 else 0.0

            adjustment.total_qty = total_qty
            adjustment.total_cost_sum = total_cost_sum
            adjustment.average_cost = average_cost

            # Automatically update all lines' cost_after_adjustment with the average cost
            if average_cost > 0 and adjustment.line_ids:
                # Update all lines without triggering write method to avoid loops
                for line in adjustment.line_ids:
                    if line.cost_after_adjustment != average_cost:
                        line.with_context(skip_update=True, auto_update=True, skip_posted_check=True).write({'cost_after_adjustment': average_cost})

    def _update_all_cost_after_adjustment(self):
        """Update all lines' cost_after_adjustment with the average cost"""
        if self.average_cost > 0:
            for line in self.line_ids:
                line.cost_after_adjustment = self.average_cost

    def write(self, vals):
        """Override write to prevent editing when posted and update cost_after_adjustment when adjustment is saved"""
        for adjustment in self:
            if adjustment.date_posted and not self.env.context.get('skip_posted_check'):
                raise UserError('You cannot edit a posted cost adjustment.')
        result = super().write(vals)
        # Update all lines after save
        for adjustment in self:
            adjustment._update_all_cost_after_adjustment()
        return result

    def action_apply_average_cost(self):
        """Button action to apply average cost to all lines"""
        for adjustment in self:
            if adjustment.average_cost > 0:
                # Update all lines' cost_after_adjustment with the average cost
                for line in adjustment.line_ids:
                    line.cost_after_adjustment = adjustment.average_cost
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Average cost applied to all lines.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_post(self):
        """Update product costs to the average cost and mark as posted"""
        for adjustment in self:
            # Ensure name is set before posting
            if not adjustment.name:
                adjustment.with_context(skip_posted_check=True).write({'name': adjustment._default_name()})
            
            if adjustment.date_posted:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Warning',
                        'message': 'This cost adjustment is already posted.',
                        'type': 'warning',
                        'sticky': False,
                    }
                }

            if not adjustment.line_ids:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Warning',
                        'message': 'Please add at least one product line before updating costs.',
                        'type': 'warning',
                        'sticky': False,
                    }
                }

            # Store average cost before updating
            avg_cost = adjustment.average_cost

            if avg_cost <= 0:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Warning',
                        'message': 'Average cost must be greater than zero.',
                        'type': 'warning',
                        'sticky': False,
                    }
                }

            # Update all products' standard_price with the average cost
            for line in adjustment.line_ids:
                if line.product_id:
                    line.product_id.write({'standard_price': avg_cost})

            # Mark as posted by setting date
            adjustment.with_context(skip_posted_check=True).write({
                'date_posted': fields.Datetime.now()
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'All product costs have been updated to {avg_cost:.2f}.',
                'type': 'success',
                'sticky': False,
            }
        }


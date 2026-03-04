# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'
    
    # Add discount_amount field to store absolute discount amount
    discount_amount = fields.Float(
        string='Discount Amount', 
        digits='Product Price', 
        default=0.0,
        help="Absolute discount amount in currency"
    )
    
    @api.model
    def _load_pos_data_fields(self, config_id):
        """Override to include discount_amount in POS data loading"""
        fields = super()._load_pos_data_fields(config_id)
        if 'discount_amount' not in fields:
            fields.append('discount_amount')
        return fields
    
    def _prepare_invoice_line(self, **optional_values):
        """Override to ensure invoice line amounts match POS order line amounts exactly."""
        # Call parent first to get base values
        res = super()._prepare_invoice_line(**optional_values)
        
        # Get exact values from POS order line
        pos_price_subtotal = self.price_subtotal
        quantity = res.get('quantity', self.qty) or 1.0
        original_price_unit = res.get('price_unit', 0)
        
        _logger.info("=== POS Invoice Line Preparation ===")
        _logger.info(f"Product: {self.product_id.name if self.product_id else 'N/A'}")
        _logger.info(f"POS price_subtotal: {pos_price_subtotal}, quantity: {quantity}")
        _logger.info(f"Original invoice price_unit from parent: {original_price_unit}")
        
        if quantity > 0 and pos_price_subtotal != 0:
            # Calculate price_unit to ensure price_subtotal matches exactly
            # price_subtotal = price_unit * quantity, so price_unit = price_subtotal / quantity
            # This ensures the invoice line subtotal matches the POS order line subtotal exactly
            exact_price_unit = pos_price_subtotal / quantity
            res['price_unit'] = exact_price_unit
            
            _logger.info(f"Calculated exact_price_unit: {exact_price_unit}")
            _logger.info(f"Expected invoice line subtotal: {exact_price_unit * quantity} (should match POS: {pos_price_subtotal})")
            _logger.info(f"Final invoice price_unit set to: {res['price_unit']}")
        
        return res

class AccountTax(models.Model):
    _inherit = 'account.tax'
    
    @api.model
    def _load_pos_data_fields(self, config_id):
        """Add invoice_label and type_tax_use to POS loaded fields"""
        fields = super()._load_pos_data_fields(config_id)
        # Add invoice_label and type_tax_use if not already present
        if 'invoice_label' not in fields:
            fields.append('invoice_label')
        if 'type_tax_use' not in fields:
            fields.append('type_tax_use')
        return fields

class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    def _create_invoice(self, move_vals):
        """Override to ensure invoice totals match POS order totals exactly."""
        invoice = super()._create_invoice(move_vals)
        
        if invoice:
            # Recompute invoice to ensure all amounts are updated
            invoice._compute_amount()
            
            # Log POS order totals and line details
            _logger.info("=== POS Invoice Creation ===")
            _logger.info(f"POS Order Total: {self.amount_total}")
            # Calculate untaxed amount if amount_tax exists
            if hasattr(self, 'amount_tax'):
                _logger.info(f"POS Order Tax: {self.amount_tax}")
                _logger.info(f"POS Order Untaxed (calculated): {self.amount_total - self.amount_tax}")
            
            # Match POS order lines with invoice lines and log/check each
            pos_lines = self.lines
            # Filter for product lines - just check for product_id (ignore display_type for now)
            invoice_lines = invoice.invoice_line_ids.filtered(lambda l: l.product_id)
            
            _logger.info(f"Found {len(invoice_lines)} invoice lines with products")
            _logger.info(f"Found {len(pos_lines)} POS order lines")
            
            # Create mapping: product_id -> pos_line
            pos_line_map = {line.product_id.id: line for line in pos_lines if line.product_id}
            _logger.info(f"POS line map has {len(pos_line_map)} products")
            
            _logger.info("=== Line-by-Line Comparison ===")
            lines_adjusted = []
            for inv_line in invoice_lines:
                product_name = inv_line.product_id.name if inv_line.product_id else 'Unknown'
                _logger.info(f"Checking invoice line: {product_name} (ID: {inv_line.product_id.id if inv_line.product_id else 'N/A'})")
                
                if inv_line.product_id and inv_line.product_id.id in pos_line_map:
                    pos_line = pos_line_map[inv_line.product_id.id]
                    _logger.info(f"Product: {product_name}")
                    _logger.info(f"  POS price_subtotal: {pos_line.price_subtotal}, Invoice price_subtotal: {inv_line.price_subtotal}")
                    _logger.info(f"  POS price_unit: {getattr(pos_line, 'price_unit', 'N/A')}, Invoice price_unit: {inv_line.price_unit}")
                    
                    # Check if there's a difference in line subtotals
                    line_diff = pos_line.price_subtotal - inv_line.price_subtotal
                    _logger.info(f"  Line difference: {line_diff}")
                    
                    if abs(line_diff) > 0.0001:
                        _logger.warning(f"  ⚠️ LINE DIFFERENCE DETECTED: {line_diff}")
                        # Adjust this line's price_unit to match POS exactly
                        if inv_line.quantity > 0:
                            target_subtotal = pos_line.price_subtotal
                            current_subtotal = inv_line.price_subtotal
                            subtotal_diff = target_subtotal - current_subtotal
                            
                            # Account for discount: price_subtotal = price_unit * quantity * (1 - discount/100)
                            discount = inv_line.discount or 0.0
                            discount_factor = (1 - discount / 100.0)
                            
                            # Calculate price_unit adjustment needed
                            if discount_factor > 0:
                                price_unit_adjustment = subtotal_diff / (inv_line.quantity * discount_factor)
                            else:
                                price_unit_adjustment = subtotal_diff / inv_line.quantity
                            
                            old_price_unit = inv_line.price_unit
                            new_price_unit = old_price_unit + price_unit_adjustment
                            
                            inv_line.write({'price_unit': new_price_unit})
                            lines_adjusted.append(product_name)
                            _logger.info(f"  ✅ Adjusted {product_name} - discount: {discount}%, discount_factor: {discount_factor}")
                            _logger.info(f"     old price_unit: {old_price_unit}, new: {new_price_unit}, adjustment: {price_unit_adjustment}")
                else:
                    _logger.warning(f"  ⚠️ No matching POS line found for invoice line: {product_name}")
            
            _logger.info(f"Adjusted {len(lines_adjusted)} lines: {lines_adjusted}")
            
            # Recompute after line adjustments
            invoice._compute_amount()
            _logger.info(f"Invoice Total After Line Adjustments: {invoice.amount_total}")
            
            # Final check: if total still doesn't match, adjust last line
            diff = self.amount_total - invoice.amount_total
            _logger.info(f"Final Difference: {diff}")
            
            if abs(diff) > 0.0001:
                # Get all invoice lines again (they might have changed after recompute)
                all_invoice_lines = invoice.invoice_line_ids
                _logger.info(f"Total invoice lines (all types): {len(all_invoice_lines)}")
                
                # Filter for product lines only - just check for product_id
                product_lines = [l for l in all_invoice_lines if l.product_id]
                _logger.info(f"Product invoice lines: {len(product_lines)}")
                
                if product_lines:
                    last_line = product_lines[-1]
                    quantity = last_line.quantity or 1.0
                    old_price_unit = last_line.price_unit
                    old_subtotal = last_line.price_subtotal
                    
                    _logger.info(f"Adjusting last line for final difference: {last_line.product_id.name}")
                    _logger.info(f"Last line - old price_unit: {old_price_unit}, quantity: {quantity}, old subtotal: {old_subtotal}")
                    
                    if quantity > 0:
                        # For final adjustment, account for discount
                        discount = last_line.discount or 0.0
                        discount_factor = (1 - discount / 100.0)
                        
                        # Calculate price_unit adjustment needed to change total by 'diff'
                        if discount_factor > 0:
                            price_adjustment = diff / (quantity * discount_factor)
                        else:
                            price_adjustment = diff / quantity
                        
                        new_price_unit = last_line.price_unit + price_adjustment
                        
                        _logger.info(f"Final adjustment - discount: {discount}%, discount_factor: {discount_factor}")
                        _logger.info(f"Applying adjustment: {price_adjustment} per unit")
                        last_line.write({'price_unit': new_price_unit})
                        _logger.info(f"Final adjustment - old price_unit: {old_price_unit}, new price_unit: {new_price_unit}")
                        
                        # Recompute to update totals
                        invoice._compute_amount()
                        final_total = invoice.amount_total
                        _logger.info(f"Final Invoice Total: {final_total} (Target POS: {self.amount_total}, Match: {abs(final_total - self.amount_total) < 0.01})")
                else:
                    _logger.error(f"No product lines found for final adjustment! All lines: {[(l.name, l.product_id.name if l.product_id else 'No product') for l in all_invoice_lines]}")
        
        return invoice

class PosConfig(models.Model):
    _inherit = 'pos.config'

    receipt_logo = fields.Binary("Receipt Logo", help="Upload a custom logo to print on POS receipts.")
    company_name = fields.Char("Store Name", help="Add store name to display on receipt.")


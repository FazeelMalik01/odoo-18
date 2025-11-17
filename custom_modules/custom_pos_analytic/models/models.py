from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero
import logging

_logger = logging.getLogger(__name__)

class PosConfig(models.Model):
    _inherit = 'pos.config'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help='Select an analytic account for this POS configuration.'
    )

class PosSession(models.Model):
    _inherit = 'pos.session'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help='Analytic account linked to this POS session.'
    )

    @api.model
    def create(self, vals):
        """Set analytic account from POS config when session is created."""
        _logger.info("=== POS SESSION DEBUG: Creating POS session ===")
        
        if not vals.get('analytic_account_id') and vals.get('config_id'):
            config = self.env['pos.config'].browse(vals['config_id'])
            if config.analytic_account_id:
                vals['analytic_account_id'] = config.analytic_account_id.id
                _logger.info(f"Set analytic account {config.analytic_account_id.id} for session from config")
        
        result = super(PosSession, self).create(vals)
        
        # Ensure analytic account is set after creation
        if not result.analytic_account_id and result.config_id and result.config_id.analytic_account_id:
            result.write({
                'analytic_account_id': result.config_id.analytic_account_id.id
            })
            _logger.info(f"Post-create: Set analytic account {result.config_id.analytic_account_id.id} for session {result.id}")
        
        return result

    def action_pos_session_open(self):
        """Override to ensure analytic account is set when session is opened."""
        _logger.info(f"=== POS SESSION DEBUG: Opening session {self.id} ===")
        
        # Ensure analytic account is set when opening session
        if not self.analytic_account_id and self.config_id and self.config_id.analytic_account_id:
            self.write({
                'analytic_account_id': self.config_id.analytic_account_id.id
            })
            _logger.info(f"Set analytic account {self.config_id.analytic_account_id.id} when opening session")
        
        return super(PosSession, self).action_pos_session_open()

    def action_pos_session_close(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """Override to set analytic account in journal entries when session closes."""
        _logger.info(f"=== POS SESSION DEBUG: Closing session {self.id} ===")

        # Ensure analytic account is set before closing
        if not self.analytic_account_id and self.config_id and self.config_id.analytic_account_id:
            self.write({
                'analytic_account_id': self.config_id.analytic_account_id.id
            })
            _logger.info(f"Set analytic account {self.config_id.analytic_account_id.id} before closing session")

        # Call original close method (creates journal entries)
        result = super(PosSession, self).action_pos_session_close(balancing_account, amount_to_balance, bank_payment_method_diffs)

        # Patch journal entry lines with analytic distribution
        for session in self:
            if session.move_id and session.analytic_account_id:
                _logger.info(f"Updating analytic distribution for move {session.move_id.id}")

                for line in session.move_id.line_ids:
                    try:
                        # Analytic distribution expects a dict like {'analytic_account_id': percentage}
                        analytic_distribution = {str(session.analytic_account_id.id): 100.0}

                        line.write({'analytic_distribution': analytic_distribution})
                        _logger.info(f"Set analytic distribution {analytic_distribution} for line {line.id}")
                    except Exception as e:
                        _logger.warning(f"Failed to set analytic distribution for line {line.id}: {e}")

        return result


    def write(self, vals):
        """Override write to ensure analytic account is preserved."""
        try:
            # If config_id is being set and no analytic_account_id, get it from config
            if vals.get('config_id') and not vals.get('analytic_account_id'):
                config = self.env['pos.config'].browse(vals['config_id'])
                if config.analytic_account_id:
                    vals['analytic_account_id'] = config.analytic_account_id.id
                    _logger.info(f"Set analytic account from config during session write: {config.analytic_account_id.id}")
        except Exception as e:
            _logger.warning(f"Error in session write method: {e}")
        
        return super(PosSession, self).write(vals)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help='Analytic account linked to this POS order.'
    )

    @api.model
    def create_from_ui(self, orders, draft=False):
        """Ensure analytic account is assigned from POS config."""
        _logger.info("=== POS ANALYTIC DEBUG: Creating POS orders from UI ===")
        
        # Process each order to set analytic account
        for order in orders:
            if isinstance(order, dict) and 'data' in order:
                data = order.get('data', {})
                config_id = data.get('config_id')
                
                if config_id:
                    try:
                        config = self.env['pos.config'].browse(config_id)
                        if config.analytic_account_id:
                            # Set analytic account in the order data
                            data['analytic_account_id'] = config.analytic_account_id.id
                            order['data'] = data
                            _logger.info(f"Set analytic account {config.analytic_account_id.id} for order")
                    except Exception as e:
                        _logger.warning(f"Error processing order: {e}")

        # Create orders using super method
        result = super(PosOrder, self).create_from_ui(orders, draft)
        
        # Post-process to ensure analytic account is set
        for order in result:
            try:
                if not order.analytic_account_id and order.config_id and order.config_id.analytic_account_id:
                    order.write({
                        'analytic_account_id': order.config_id.analytic_account_id.id
                    })
                    _logger.info(f"Post-process: Set analytic account {order.config_id.analytic_account_id.id} for order {order.id}")
            except Exception as e:
                _logger.warning(f"Error post-processing order {order.id}: {e}")
        
        return result

    @api.model
    def create(self, vals):
        """Also handle manual creation or backend imports."""
        _logger.info(f"=== POS ANALYTIC DEBUG: Creating POS order ===")
        _logger.info(f"Create vals: {vals}")
        
        if not vals.get('analytic_account_id') and vals.get('config_id'):
            config = self.env['pos.config'].browse(vals['config_id'])
            if config.analytic_account_id:
                vals['analytic_account_id'] = config.analytic_account_id.id
                _logger.info(f"Set analytic account {config.analytic_account_id.id} during create")
        
        result = super(PosOrder, self).create(vals)
        
        # Ensure analytic account is set after creation
        if not result.analytic_account_id and result.config_id and result.config_id.analytic_account_id:
            result.write({
                'analytic_account_id': result.config_id.analytic_account_id.id
            })
            _logger.info(f"Post-create: Set analytic account {result.config_id.analytic_account_id.id} for order {result.id}")
        
        return result

    def _action_create_sale_order(self, vals):
        """Override to ensure analytic account is passed to sale order."""
        _logger.info(f"Creating sale order for POS order {self.id} with analytic account: {self.analytic_account_id}")
        
        sale_order = super(PosOrder, self)._action_create_sale_order(vals)
        
        # Set analytic account on the sale order
        if self.analytic_account_id and sale_order:
            _logger.info(f"Setting analytic account {self.analytic_account_id.id} on sale order {sale_order.id}")
            sale_order.write({
                'analytic_account_id': self.analytic_account_id.id
            })
            
            # Also set analytic account on sale order lines
            for line in sale_order.order_line:
                line.write({
                    'analytic_account_id': self.analytic_account_id.id
                })
                _logger.info(f"Set analytic account on sale order line {line.id}")
        
        return sale_order

    @api.model
    def _order_fields(self, ui_order):
        """Override to ensure analytic account is included in order fields."""
        try:
            # Get the analytic account from config if not already set
            if not ui_order.get('analytic_account_id') and ui_order.get('config_id'):
                config = self.env['pos.config'].browse(ui_order['config_id'])
                if config.analytic_account_id:
                    ui_order['analytic_account_id'] = config.analytic_account_id.id
                    _logger.info(f"Set analytic account from config: {config.analytic_account_id.id}")
        except Exception as e:
            _logger.warning(f"Error in _order_fields: {e}")
        
        return super(PosOrder, self)._order_fields(ui_order)

    @api.model
    def _load_onboarding_pos_config(self):
        """Override to ensure analytic account is loaded."""
        _logger.info("=== POS ANALYTIC DEBUG: Loading onboarding config ===")
        result = super(PosOrder, self)._load_onboarding_pos_config()
        return result

    def write(self, vals):
        """Override write to ensure analytic account is preserved."""
        try:
            # If config_id is being set and no analytic_account_id, get it from config
            if vals.get('config_id') and not vals.get('analytic_account_id'):
                config = self.env['pos.config'].browse(vals['config_id'])
                if config.analytic_account_id:
                    vals['analytic_account_id'] = config.analytic_account_id.id
                    _logger.info(f"Set analytic account from config during write: {config.analytic_account_id.id}")
        except Exception as e:
            _logger.warning(f"Error in write method: {e}")
        
        return super(PosOrder, self).write(vals)

    @api.model
    def _ensure_analytic_account(self):
        """Ensure all POS orders have analytic account set from their config."""
        _logger.info("=== POS ANALYTIC DEBUG: Ensuring analytic accounts are set ===")
        
        orders_without_analytic = self.search([
            ('analytic_account_id', '=', False),
            ('config_id', '!=', False)
        ])
        
        for order in orders_without_analytic:
            if order.config_id.analytic_account_id:
                order.write({
                    'analytic_account_id': order.config_id.analytic_account_id.id
                })
                _logger.info(f"Set analytic account {order.config_id.analytic_account_id.id} for order {order.id}")
        
        return True

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override read_group to ensure analytic accounts are set."""
        result = super(PosOrder, self).read_group(domain, fields, groupby, offset, limit, orderby, lazy)
        return result


    def action_set_analytic_account(self):
        """Manual method to set analytic account from config."""
        _logger.info(f"=== POS ANALYTIC DEBUG: Manually setting analytic account for order {self.id} ===")
        
        if self.config_id and self.config_id.analytic_account_id:
            self.write({
                'analytic_account_id': self.config_id.analytic_account_id.id
            })
            _logger.info(f"Set analytic account {self.config_id.analytic_account_id.id} for order {self.id}")
            return True
        else:
            _logger.warning(f"No analytic account configured for config {self.config_id}")
            return False

    def _get_invoice_lines_values(self, line_values, pos_order_line):
        """Override to add analytic distribution to invoice lines."""
        result = super(PosOrder, self)._get_invoice_lines_values(line_values, pos_order_line)
        
        # Get analytic account from order or config
        analytic_account_id = self.analytic_account_id or (self.config_id and self.config_id.analytic_account_id)
        
        if analytic_account_id:
            # Set analytic distribution in the format expected by Odoo
            analytic_distribution = {str(analytic_account_id.id): 100.0}
            result['analytic_distribution'] = analytic_distribution
            _logger.info(f"Added analytic distribution {analytic_distribution} to invoice line for order {self.id}")
        
        return result

    def _prepare_invoice_vals(self):
        """Override to ensure analytic account is available when preparing invoice."""
        _logger.info(f"=== POS ANALYTIC DEBUG: Preparing invoice vals for order {self.id} ===")
        
        # Ensure analytic account is set before creating invoice
        if not self.analytic_account_id and self.config_id and self.config_id.analytic_account_id:
            self.write({
                'analytic_account_id': self.config_id.analytic_account_id.id
            })
            _logger.info(f"Set analytic account {self.config_id.analytic_account_id.id} before invoice creation")
        
        return super(PosOrder, self)._prepare_invoice_vals()

    def _create_invoice(self, move_vals):
        """Override to set analytic account on invoice after creation."""
        _logger.info(f"=== POS ANALYTIC DEBUG: Creating invoice for order {self.id} ===")
        
        # Ensure analytic account is set before creating invoice
        analytic_account_id = self.analytic_account_id or (self.config_id and self.config_id.analytic_account_id)
        
        if analytic_account_id:
            _logger.info(f"Order has analytic account {analytic_account_id.id}, will be applied to invoice lines")
        
        # Create invoice using super method
        invoice = super(PosOrder, self)._create_invoice(move_vals)
        
        # Post-process invoice lines to ensure analytic distribution is set
        if analytic_account_id and invoice:
            analytic_distribution = {str(analytic_account_id.id): 100.0}
            
            # Set analytic distribution on invoice lines
            for line in invoice.invoice_line_ids:
                if not line.analytic_distribution:
                    line.write({'analytic_distribution': analytic_distribution})
                    _logger.info(f"Set analytic distribution {analytic_distribution} on invoice line {line.id}")
                else:
                    _logger.info(f"Invoice line {line.id} already has analytic distribution: {line.analytic_distribution}")
            
            # Set analytic distribution on all journal entry lines including receivable
            for move_line in invoice.line_ids:
                if not move_line.analytic_distribution:
                    move_line.write({'analytic_distribution': analytic_distribution})
                    _logger.info(f"Set analytic distribution {analytic_distribution} on journal entry line {move_line.id} (account: {move_line.account_id.code})")
                else:
                    _logger.info(f"Journal entry line {move_line.id} already has analytic distribution: {move_line.analytic_distribution}")
        
        return invoice


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """Override to ensure analytic distribution is set on receivable lines when invoice is posted."""
        result = super(AccountMove, self).action_post()
        
        # Check if this invoice is linked to a POS order
        for move in self:
            if move.pos_order_ids:
                _logger.info(f"=== ACCOUNT MOVE ANALYTIC DEBUG: Posting invoice {move.id} linked to POS orders ===")
                
                # Get analytic account from POS order
                pos_order = move.pos_order_ids[0]  # Get first POS order
                analytic_account_id = pos_order.analytic_account_id or (
                    pos_order.config_id and pos_order.config_id.analytic_account_id
                )
                
                if analytic_account_id:
                    analytic_distribution = {str(analytic_account_id.id): 100.0}
                    _logger.info(f"Found analytic account {analytic_account_id.id} from POS order {pos_order.id}")
                    
                    # Set analytic distribution on all journal entry lines including receivable
                    for line in move.line_ids:
                        if not line.analytic_distribution:
                            line.write({'analytic_distribution': analytic_distribution})
                            _logger.info(f"Set analytic distribution {analytic_distribution} on journal entry line {line.id} (account: {line.account_id.code if line.account_id else 'N/A'})")
                        else:
                            _logger.info(f"Journal entry line {line.id} already has analytic distribution: {line.analytic_distribution}")
        
        return result

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        """Override to add analytic distribution to Stock Interim lines in invoices."""
        _logger.info(f"=== ACCOUNT MOVE ANALYTIC DEBUG: Preparing anglo saxon out lines for move {self.id} ===")
        
        # Call parent method to get the line values
        lines_vals_list = super(AccountMove, self)._stock_account_prepare_anglo_saxon_out_lines_vals()
        
        # Check if this invoice is linked to a POS order
        for move in self:
            if move.pos_order_ids:
                # Get analytic account from POS order
                pos_order = move.pos_order_ids[0]  # Get first POS order
                analytic_account_id = pos_order.analytic_account_id or (
                    pos_order.config_id and pos_order.config_id.analytic_account_id
                )
                
                if analytic_account_id:
                    analytic_distribution = {str(analytic_account_id.id): 100.0}
                    _logger.info(f"Found analytic account {analytic_account_id.id} from POS order {pos_order.id}, adding to Stock Interim lines")
                    
                    # Add analytic distribution to Stock Interim lines (lines with display_type='cogs' and negative amount_currency)
                    for line_vals in lines_vals_list:
                        # Stock Interim line is the one with negative amount_currency and display_type='cogs'
                        # The expense line already has analytic_distribution from the invoice line
                        if line_vals.get('display_type') == 'cogs' and line_vals.get('amount_currency', 0) < 0:
                            if not line_vals.get('analytic_distribution'):
                                line_vals['analytic_distribution'] = analytic_distribution
                                _logger.info(f"Added analytic distribution {analytic_distribution} to Stock Interim line (account: {line_vals.get('account_id')})")
        
        return lines_vals_list


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        """Override to set pos_order_id before _action_done is called."""
        _logger.info("=== STOCK PICKING ANALYTIC DEBUG: Creating picking from POS order lines ===")
        
        # Get the POS order from the lines (pos.order.line has order_id field)
        pos_order = None
        if lines and hasattr(lines, 'order_id') and lines[0].order_id:
            pos_order = lines[0].order_id
            _logger.info(f"Found POS order {pos_order.id} from order lines")
        
        # We need to completely override this method to set pos_order_id before _action_done
        pickings = self.env['stock.picking']
        stockable_lines = lines.filtered(lambda l: l.product_id.type == 'consu' and not float_is_zero(l.qty, precision_rounding=l.product_id.uom_id.rounding))
        if not stockable_lines:
            return pickings
        positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
        negative_lines = stockable_lines - positive_lines

        if positive_lines:
            location_id = picking_type.default_location_src_id.id
            positive_picking = self.env['stock.picking'].create(
                self._prepare_picking_vals(partner, picking_type, location_id, location_dest_id)
            )
            
            # Set pos_order_id BEFORE _action_done is called
            if pos_order:
                positive_picking.write({
                    'pos_session_id': pos_order.session_id.id if pos_order.session_id else False,
                    'pos_order_id': pos_order.id,
                    'origin': pos_order.name
                })
                _logger.info(f"Set pos_order_id {pos_order.id} on picking {positive_picking.id} before _action_done")

            positive_picking._create_move_from_pos_order_lines(positive_lines)
            self.env.flush_all()
            try:
                with self.env.cr.savepoint():
                    positive_picking._action_done()
            except (UserError, ValidationError):
                pass

            pickings |= positive_picking
            
        if negative_lines:
            if picking_type.return_picking_type_id:
                return_picking_type = picking_type.return_picking_type_id
                return_location_id = return_picking_type.default_location_dest_id.id
            else:
                return_picking_type = picking_type
                return_location_id = picking_type.default_location_src_id.id

            negative_picking = self.env['stock.picking'].create(
                self._prepare_picking_vals(partner, return_picking_type, location_dest_id, return_location_id)
            )
            
            # Set pos_order_id BEFORE _action_done is called
            if pos_order:
                negative_picking.write({
                    'pos_session_id': pos_order.session_id.id if pos_order.session_id else False,
                    'pos_order_id': pos_order.id,
                    'origin': pos_order.name
                })
                _logger.info(f"Set pos_order_id {pos_order.id} on picking {negative_picking.id} before _action_done")

            negative_picking._create_move_from_pos_order_lines(negative_lines)
            self.env.flush_all()
            try:
                with self.env.cr.savepoint():
                    negative_picking._action_done()
            except (UserError, ValidationError):
                pass
            pickings |= negative_picking
            
        return pickings


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        """Override to add analytic distribution from POS order to stock valuation entries."""
        _logger.info(f"=== STOCK MOVE ANALYTIC DEBUG: Generating valuation lines for move {self.id} ===")
        _logger.info(f"Move picking_id: {self.picking_id.id if self.picking_id else None}")
        _logger.info(f"Move picking pos_order_id: {self.picking_id.pos_order_id.id if (self.picking_id and self.picking_id.pos_order_id) else None}")
        _logger.info(f"Move picking origin: {self.picking_id.origin if self.picking_id else None}")
        _logger.info(f"Move picking session_id: {self.picking_id.pos_session_id.id if (self.picking_id and self.picking_id.pos_session_id) else None}")
        
        # Call parent method to get base line values
        result = super(StockMove, self)._generate_valuation_lines_data(
            partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description
        )
        
        # Get analytic account from POS order if this move is related to a POS order
        analytic_account_id = None
        pos_order = None
        
        try:
            # Method 1: Check if picking has pos_order_id directly
            if self.picking_id and self.picking_id.pos_order_id:
                pos_order = self.picking_id.pos_order_id
                _logger.info(f"Found POS order {pos_order.id} from picking.pos_order_id")
            
            # Method 2: Try to find POS order by origin (POS order name)
            elif self.picking_id and self.picking_id.origin:
                pos_order = self.env['pos.order'].search([
                    ('name', '=', self.picking_id.origin)
                ], limit=1)
                if pos_order:
                    _logger.info(f"Found POS order {pos_order.id} from picking origin: {self.picking_id.origin}")
            
            # Method 3: Try to find POS order by session_id
            elif self.picking_id and self.picking_id.pos_session_id:
                # Get the most recent order from this session
                pos_order = self.env['pos.order'].search([
                    ('session_id', '=', self.picking_id.pos_session_id.id),
                    ('name', '=', self.picking_id.origin)
                ], limit=1, order='id desc')
                if pos_order:
                    _logger.info(f"Found POS order {pos_order.id} from session {self.picking_id.pos_session_id.id}")
            
            # Method 4: Check procurement group
            if not pos_order and self.group_id and hasattr(self.group_id, 'pos_order_id') and self.group_id.pos_order_id:
                pos_order = self.group_id.pos_order_id
                _logger.info(f"Found POS order {pos_order.id} from procurement group")
            
            # Get analytic account from POS order
            if pos_order:
                analytic_account_id = pos_order.analytic_account_id or (
                    pos_order.config_id and pos_order.config_id.analytic_account_id
                )
                if analytic_account_id:
                    _logger.info(f"Found analytic account {analytic_account_id.id} from POS order {pos_order.id}")
                else:
                    _logger.warning(f"POS order {pos_order.id} has no analytic account configured")
            else:
                _logger.warning(f"Could not find POS order for move {self.id}")
                
        except Exception as e:
            _logger.warning(f"Error getting analytic account from POS order: {e}")
        
        # If no analytic account from POS order, check if already set in SVL
        if not analytic_account_id:
            try:
                svl = self.env['stock.valuation.layer'].browse(svl_id)
                if svl.exists() and svl.account_move_line_id and svl.account_move_line_id.analytic_distribution:
                    # Already has analytic distribution, use it
                    _logger.info(f"Using existing analytic distribution from SVL account move line")
                    return result
            except Exception as e:
                _logger.warning(f"Error checking SVL analytic distribution: {e}")
        
        # Add analytic distribution to all line values if we have an analytic account
        if analytic_account_id:
            analytic_distribution = {str(analytic_account_id.id): 100.0}
            _logger.info(f"Adding analytic distribution {analytic_distribution} to stock valuation lines")
            
            # Add to credit line
            if 'credit_line_vals' in result:
                result['credit_line_vals']['analytic_distribution'] = analytic_distribution
            
            # Add to debit line
            if 'debit_line_vals' in result:
                result['debit_line_vals']['analytic_distribution'] = analytic_distribution
            
            # Add to price diff line if it exists
            if 'price_diff_line_vals' in result:
                result['price_diff_line_vals']['analytic_distribution'] = analytic_distribution
        else:
            _logger.warning(f"No analytic account found for move {self.id}, skipping analytic distribution")
        
        return result


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _validate_accounting_entries(self):
        """Override to ensure analytic distribution is set on stock valuation journal entries."""
        _logger.info("=== STOCK VALUATION LAYER DEBUG: Validating accounting entries ===")
        
        # Call parent method to create account moves
        result = super(StockValuationLayer, self)._validate_accounting_entries()
        
        # Post-process account moves to ensure analytic distribution is set
        for svl in self:
            if not svl.account_move_id:
                continue
            
            _logger.info(f"Processing SVL {svl.id}, account_move_id: {svl.account_move_id.id}")
            
            # Get analytic account from POS order if available
            analytic_account_id = None
            pos_order = None
            
            try:
                if svl.stock_move_id and svl.stock_move_id.picking_id:
                    picking = svl.stock_move_id.picking_id
                    
                    # Method 1: Check if picking has pos_order_id directly
                    if picking.pos_order_id:
                        pos_order = picking.pos_order_id
                        _logger.info(f"Found POS order {pos_order.id} from picking.pos_order_id for SVL {svl.id}")
                    
                    # Method 2: Try to find POS order by origin (POS order name)
                    elif picking.origin:
                        pos_order = self.env['pos.order'].search([
                            ('name', '=', picking.origin)
                        ], limit=1)
                        if pos_order:
                            _logger.info(f"Found POS order {pos_order.id} from picking origin: {picking.origin} for SVL {svl.id}")
                    
                    # Method 3: Try to find POS order by session_id
                    elif picking.pos_session_id:
                        pos_order = self.env['pos.order'].search([
                            ('session_id', '=', picking.pos_session_id.id),
                            ('name', '=', picking.origin)
                        ], limit=1, order='id desc')
                        if pos_order:
                            _logger.info(f"Found POS order {pos_order.id} from session {picking.pos_session_id.id} for SVL {svl.id}")
                    
                    # Method 4: Check procurement group
                    if not pos_order and svl.stock_move_id.group_id and hasattr(svl.stock_move_id.group_id, 'pos_order_id') and svl.stock_move_id.group_id.pos_order_id:
                        pos_order = svl.stock_move_id.group_id.pos_order_id
                        _logger.info(f"Found POS order {pos_order.id} from procurement group for SVL {svl.id}")
                    
                    # Get analytic account from POS order
                    if pos_order:
                        analytic_account_id = pos_order.analytic_account_id or (
                            pos_order.config_id and pos_order.config_id.analytic_account_id
                        )
                        if analytic_account_id:
                            _logger.info(f"Found analytic account {analytic_account_id.id} from POS order {pos_order.id} for SVL {svl.id}")
                        else:
                            _logger.warning(f"POS order {pos_order.id} has no analytic account configured for SVL {svl.id}")
                    else:
                        _logger.warning(f"Could not find POS order for SVL {svl.id}")
                        
            except Exception as e:
                _logger.warning(f"Error getting analytic account from POS order for SVL {svl.id}: {e}")
            
            # Update account move lines with analytic distribution if we have an analytic account
            if analytic_account_id and svl.account_move_id:
                analytic_distribution = {str(analytic_account_id.id): 100.0}
                _logger.info(f"Updating account move {svl.account_move_id.id} with analytic distribution {analytic_distribution}")
                
                for line in svl.account_move_id.line_ids:
                    if not line.analytic_distribution:
                        try:
                            line.write({'analytic_distribution': analytic_distribution})
                            _logger.info(f"Set analytic distribution on account move line {line.id}")
                        except Exception as e:
                            _logger.warning(f"Failed to set analytic distribution on line {line.id}: {e}")
                    else:
                        _logger.info(f"Account move line {line.id} already has analytic distribution: {line.analytic_distribution}")
        
        return result


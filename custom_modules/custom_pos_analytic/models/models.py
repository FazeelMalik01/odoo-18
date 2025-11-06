from odoo import models, fields, api
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


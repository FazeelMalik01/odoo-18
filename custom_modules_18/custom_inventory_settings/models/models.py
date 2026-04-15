from odoo import models, fields, api
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        help="Select the employee responsible for this transfer."
    )

    def button_validate(self):
        """Intercept validate button and ask for PIN before validating."""
        self.ensure_one()

        # Require employee first
        if not self.employee_id:
            raise UserError("Please select an employee before validating.")

        # If the context says PIN was already verified → run default validation
        if self.env.context.get('pin_verified'):
            return super(StockPicking, self).button_validate()

        # Otherwise open the wizard for PIN entry
        return {
            'name': 'Employee PIN Verification',
            'type': 'ir.actions.act_window',
            'res_model': 'employee.pin.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.employee_id.id,
                'active_model': self._name,
                'active_id': self.id,
            },
        }
    
    def action_cancel(self):
        self.ensure_one()

        # ❌ Prevent cancelling POS deliveries
        if self.picking_type_id and self.picking_type_id.name == 'PoS Orders':
            raise UserError("POS deliveries cannot be cancelled.")

        # Require employee
        if not self.employee_id:
            raise UserError("Please select an employee before cancelling.")

        # If PIN already verified → proceed with cancel
        if self.env.context.get('pin_verified_cancel'):
            res = super().action_cancel()

            # Log employee name
            self.message_post(
                body=f"Transfer cancelled by <b>{self.employee_id.name}</b>"
            )

            return res

        # Otherwise open wizard
        return {
            'name': 'Employee PIN Verification',
            'type': 'ir.actions.act_window',
            'res_model': 'employee.pin.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.employee_id.id,
                'active_model': self._name,
                'active_id': self.id,
                'cancel_flow': True,
            },
        }

class EmployeePinWizard(models.TransientModel):
    _name = 'employee.pin.wizard'
    _description = 'Employee PIN Verification Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True)
    entered_pin = fields.Char(string='Enter PIN', required=True, password=True, groups="base.group_user")

    def action_confirm_pin(self):
        picking = self.env[self.env.context.get('active_model')].browse(
            self.env.context.get('active_id')
        )

        # Check PIN
        if self.entered_pin != self.employee_id.pin:
            raise UserError("Invalid PIN.")

        # Cancel flow
        if self.env.context.get('cancel_flow'):
            return picking.with_context(pin_verified_cancel=True).action_cancel()

        # Validation flow
        return picking.with_context(pin_verified=True).button_validate()

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    product_cost = fields.Float(
        compute="_compute_product_cost",
        string="Cost Price",
        store=True
    )

    @api.depends('product_id')
    def _compute_product_cost(self):
        for line in self:
            # Safely read standard_price whether it's float or JSONB
            try:
                cost_value = line.product_id.standard_price
                # If standard_price is JSONB (dict), extract the 'value' or 'amount'
                if isinstance(cost_value, dict):
                    cost_value = cost_value.get('amount', 0.0) or cost_value.get('value', 0.0)
            except Exception:
                cost_value = 0.0
            line.product_cost = float(cost_value or 0.0)


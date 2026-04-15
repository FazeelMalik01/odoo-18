from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ServiceTaskPinWizard(models.TransientModel):
    _name = 'service.task.pin.wizard'
    _description = 'Service Task PIN Authentication'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True
    )
    pin = fields.Char(
        string='PIN',
        required=True,
        password=True
    )

    def action_validate_pin(self):
        self.ensure_one()
        employee = self.employee_id

        if not employee.pin:
            raise ValidationError(_("This employee has no PIN configured."))

        if self.pin != employee.pin:
            raise ValidationError(_("Incorrect PIN. Please try again."))

        user = employee.user_id
        if not user:
            raise ValidationError(_("This employee has no linked user account."))

        kiosk_menu_id = self.env.ref(
            'advance_vehicle_repair.menu_service_tasks_kiosk_child'
        ).id

        return {
            'type': 'ir.actions.client',
            'tag': 'kiosk_redirect',
            'params': {
                'menu_id': kiosk_menu_id,
                'authenticated_employee_id': employee.id,
                'domain': [('assigners_user_ids', 'in', user.ids)],
                'context': {
                    'group_by': 'state',
                    'authenticated_employee_id': employee.id,
                },
            },
        }
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    service_request_ids = fields.One2many(
        'service.request',
        'sale_order_id',
        string='Service Requests'
    )

    def action_create_work_order(self):
        """Create Work Orders manually from button."""
        self.ensure_one()

        if not self.service_request_ids:
            raise UserError("No Service Requests found for this Sale Order.")

        Task = self.env['project.task'].sudo()

        created_tasks = self.env['project.task']

        for sr in self.service_request_ids:

            # Prevent duplicates
            existing = Task.search([('service_request_id', '=', sr.id)], limit=1)
            if existing:
                created_tasks |= existing
                continue

            task = Task.create({
                'name': f"{sr.name or 'Service Request'} - {sr.customer_id.name}",
                'service_request_id': sr.id,
                'sale_order_id': self.id,
                'estimate_id': self.id,

                # Patch default project.task fields
                'partner_id': sr.customer_id.id,
                'partner_phone': sr.primary_phone,
                'date_deadline': sr.requested_appointment,

                # Project optional (task is not required to belong to one)
                # project_id: optional — if you want, you can assign
            })

            created_tasks |= task

            _logger.info("Created Work Order %s for Service Request %s", task.id, sr.id)

        # Open the first task
        return {
            'name': "Work Order",
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': created_tasks[0].id,
            'target': 'current',
        }

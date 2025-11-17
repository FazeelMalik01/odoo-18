from odoo import models, fields


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # Link back to service request & sale order
    service_request_id = fields.Many2one(
        'service.request',
        string='Service Request',
        ondelete='set null',
        index=True
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Related Sale Order',
        ondelete='set null',
        index=True
    )

    # Secure Notes (security restricted)
    secure_notes = fields.Text(
        string='Secure Notes',
        groups='custom_gatekeeper_security.group_service_secure_notes'
    )

    # Photos (attachments)
    photo_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        domain=[('res_model', '=', 'project.task')],
        string="Photos"
    )

    # Customer SMS Thread
    sms_thread = fields.Text(string="Customer SMS Thread")

    # Estimate Reference
    estimate_id = fields.Many2one('sale.order', string='Estimate / Quotation')

    # Deposit Status
    deposit_status = fields.Selection([
        ('not_requested', 'Not Requested'),
        ('requested', 'Requested'),
        ('paid', 'Paid'),
    ], string='Deposit Status', default='not_requested')

    # Gating Status
    gating_status = fields.Selection([
        ('pending', 'Pending'),
        ('blocked', 'Blocked'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
    ], string="Gating Status", default='pending')
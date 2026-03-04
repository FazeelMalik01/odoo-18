# -*- coding: utf-8 -*-
from odoo import models, fields, api
from markupsafe import escape as html_escape
import logging

_logger = logging.getLogger(__name__)


class WorkOrderWorksheet(models.Model):
    _name = 'work.order.worksheet'
    _description = 'Work Order Worksheet'
    _order = 'create_date desc'

    name = fields.Char(string='Worksheet Number', required=True, copy=False, readonly=True, default=lambda self: 'New')
    task_id = fields.Many2one('project.task', string='Work Order', required=True, ondelete='cascade', index=True)
    service_request_id = fields.Many2one('service.request', string='Service Request', related='task_id.service_request_id', store=True, readonly=True)
    
    # Work execution data
    state = fields.Selection([
        ('01_in_progress', 'In Progress'),
        ('02_changes_requested', 'Changes Requested'),
        ('03_approved', 'Approved'),
        ('1_done', 'Done'),
        ('1_canceled', 'Cancelled'),
        ('04_waiting_normal', 'Waiting'),
    ], string='Task Status', required=True)
    
    gating_status = fields.Selection([
        ('pending', 'Pending'),
        ('blocked', 'Blocked'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
    ], string='Gating Status', related='task_id.gating_status', store=True, readonly=True)
    
    # Work details
    work_images = fields.Many2many('ir.attachment', 'worksheet_images_rel', 'worksheet_id', 'attachment_id',
                                   string='Work Images', copy=True)
    work_images_html = fields.Html(string='Work Images Display', compute='_compute_work_images_html', sanitize=False)
    material_used = fields.Text(string='Material Used')
    work_notes = fields.Text(string='Work Notes')
    sms_message = fields.Text(string='SMS Message Sent')
    
    # Time tracking
    timer_hours = fields.Float(string='Timer Hours', help='Time tracked by timer')
    allocated_hours = fields.Float(string='Allocated Hours', help='Manually allocated hours')
    
    # Technician info
    technician_id = fields.Many2one('res.users', string='Technician', required=True, default=lambda self: self.env.user)
    completion_date = fields.Datetime(string='Completion Date', default=fields.Datetime.now, required=True)
    
    # Customer info (from service request)
    customer_id = fields.Many2one('res.partner', string='Customer', related='service_request_id.customer_id', store=True, readonly=True)
    service_address = fields.Text(string='Service Address', related='service_request_id.service_address', readonly=True)
    
    # Active field
    active = fields.Boolean(string='Active', default=True)

    @api.depends('work_images')
    def _compute_work_images_html(self):
        """Compute HTML display for work images in gallery format"""
        for record in self:
            if record.work_images:
                html_parts = ['<div class="row" style="margin: 0;">']
                for image in record.work_images:
                    image_url = f'/web/image/ir.attachment/{image.id}/datas'
                    image_name = html_escape(image.name or 'Image')
                    html_parts.append(f'''
                        <div class="col-md-3 mb-3" style="padding: 5px;">
                            <div class="card" style="height: 100%; border: 1px solid #dee2e6; border-radius: 0.25rem;">
                                <a href="{image_url}" target="_blank" style="text-decoration: none;">
                                    <img src="{image_url}" 
                                         class="card-img-top" 
                                         style="height: 200px; object-fit: cover; cursor: pointer; width: 100%; border-radius: 0.25rem 0.25rem 0 0;"
                                         alt="{image_name}"/>
                                </a>
                                <div class="card-body p-2">
                                    <small class="text-muted d-block" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{image_name}">{image_name}</small>
                                </div>
                            </div>
                        </div>
                    ''')
                html_parts.append('</div>')
                record.work_images_html = ''.join(html_parts)
            else:
                record.work_images_html = '<div class="text-muted">No images uploaded</div>'

    @api.model
    def create(self, vals):
        """Generate worksheet number"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('work.order.worksheet') or 'New'
        return super(WorkOrderWorksheet, self).create(vals)


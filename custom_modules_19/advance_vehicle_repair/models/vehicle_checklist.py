from odoo import models, fields, api

class VehicleChecklist(models.Model):
    _name = 'vehicle.checklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Vehicle Checklist Templates'

    name = fields.Char(string="Name", required=True, tracking=True)
    checklist_line_ids = fields.One2many('vehicle.checklist.line', 'checklist_id', string='Checklist Items', tracking=True)

class VehicleChecklistLine(models.Model):
    _name = 'vehicle.checklist.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Vehicle Checklist Line Items'
    _rec_name = 'name'

    name = fields.Char(string="Name", store=True, tracking=True)
    is_checked = fields.Boolean(string="Is Checked", default=False)
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
        ('line_item', 'Item'),
    ], string='Display Type', default='line_item', tracking=True)
    checklist_id = fields.Many2one('vehicle.checklist', string="Checklist", tracking=True)
    jobcard_id = fields.Many2one('vehicle.jobcard', string='Jobcard Id')


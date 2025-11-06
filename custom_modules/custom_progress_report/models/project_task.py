from odoo import models, fields

class ProjectTask(models.Model):
    _inherit = 'project.task'

    planned_quantity = fields.Float(string="Planned Quantity")
    unit = fields.Many2one('uom.uom', string="Unit")
    progress_report_ids = fields.One2many(
        'custom.progress.report',
        'task_name',
        string="Daily Progress Reports"
    )
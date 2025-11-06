from odoo import models, fields, api

class ProgressReport(models.Model):
    _name = 'custom.progress.report'
    _description = 'Daily Progress Report'

    task_name = fields.Many2one('project.task', string="Task Name")
    task_description = fields.Text("Task Description")
    date = fields.Date("Date", default=fields.Date.today)
    done_quantity = fields.Float("Done Quantity")
    planned_quantity = fields.Float("Planned Quantity")
    unit = fields.Char("Unit")
    task_image = fields.Binary("Task Image", attachment=True)
    task_image_mimetype = fields.Char("Task Image MIME Type")
    user_id = fields.Many2one('res.users', string="Created By", default=lambda self: self.env.user)
    progress_rate = fields.Float(string="Progress Rate (%)", compute="_compute_progress_rate", store=True)
    report_batch_id = fields.Char(string="Batch ID")

    @api.depends('done_quantity', 'planned_quantity')
    def _compute_progress_rate(self):
        for rec in self:
            if rec.planned_quantity > 0:
                rec.progress_rate = (rec.done_quantity / rec.planned_quantity) * 100
            else:
                rec.progress_rate = 0.0
    
    # ✅ Auto-fill fields when task is selected
    @api.onchange('task_name')
    def _onchange_task_name(self):
        if self.task_name:
            self.task_description = self.task_name.description or ''
            self.planned_quantity = self.task_name.planned_quantity or 0.0
            self.unit = self.task_name.unit_id.name if self.task_name.unit_id else ''
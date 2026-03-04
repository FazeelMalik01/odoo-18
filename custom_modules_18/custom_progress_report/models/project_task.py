from odoo import models, fields, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    planned_quantity = fields.Float(string="Planned Quantity")
    unit = fields.Many2one('uom.uom', string="Unit")
    progress_report_ids = fields.One2many(
        'custom.progress.report',
        'task_name',
        string="Daily Progress Reports"
    )
    all_progress_report_ids = fields.Many2many(
        'custom.progress.report',
        string="All Progress Reports (Including Subtasks)",
        compute="_compute_all_progress_report_ids",
        store=False,
    )
    # allocated_days = fields.Float(string="Allocated Days")
    time_ratio = fields.Float(string="Time Spent (Days)", compute="_compute_time_ratio", store=False)
    time_ratio_display = fields.Char(string="Time Spent (Days) Display", compute="_compute_time_ratio_display", store=False)

    def _compute_time_ratio(self):
        for task in self:
            # Safely access effective_hours (from hr_timesheet module) in case it's not available
            # Field is non-stored so it always computes fresh when accessed
            effective_hours = getattr(task, 'effective_hours', 0.0) or 0.0
            allocated_hours = getattr(task, 'allocated_hours', 0.0) or 0.0
            
            if allocated_hours and allocated_hours > 0:
                task.time_ratio = effective_hours / allocated_hours
            else:
                task.time_ratio = 0.0

    def _compute_time_ratio_display(self):
        for task in self:
            effective_hours = getattr(task, 'effective_hours', 0.0) or 0.0
            allocated_hours = getattr(task, 'allocated_hours', 0.0) or 0.0
            
            if allocated_hours and allocated_hours > 0:
                eff_days = round(effective_hours / 8.0, 2)
                alloc_days = round(allocated_hours / 8.0, 2)
                task.time_ratio_display = f"{int(round(eff_days))} / {int(round(alloc_days))} days"
            else:
                task.time_ratio_display = "0 / 0 days"
                
    @api.depends('progress_report_ids', 'child_ids', 'child_ids.progress_report_ids')
    def _compute_all_progress_report_ids(self):
        for task in self:
            # Start with reports from the main task
            all_reports = task.progress_report_ids
            
            # Add reports from all subtasks
            if task.child_ids:
                for subtask in task.child_ids:
                    all_reports |= subtask.progress_report_ids
            
            task.all_progress_report_ids = all_reports
from odoo import models, fields, api

class RepairTechnicianWizard(models.TransientModel):
    _name = 'repair.technician.wizard'
    _description = 'Select Technician'

    repair_line_id = fields.Many2one('vehicle.repair.services.line', required=True)
    employee_id = fields.Many2one('hr.employee', string="Technician", required=True)
    team_employee_ids = fields.Many2many('hr.employee', compute="_compute_team_employees")

    @api.depends('repair_line_id')
    def _compute_team_employees(self):
        for rec in self:
            rec.team_employee_ids = rec.repair_line_id.service_team.team_employee_ids.mapped('employee_id')

    def action_start_timer(self):
        self.ensure_one()
        line = self.repair_line_id
        employee = self.employee_id

        # Add employee to assigners if not already there
        if employee not in line.assigners.mapped('employee_id'):
            team_line = line.service_team.team_employee_ids.filtered(lambda t: t.employee_id == employee)
            line.assigners = [(4, team_line.id)]

        # Start timer
        line._start_employee_timer(employee)

        return {'type': 'ir.actions.act_window_close'}
from odoo import fields, models, api

class VehicleTeams(models.Model):
    _name = 'vehicle.teams'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Vehicle Teams"
    _rec_name = 'team_title'

    team_title=fields.Char(string='Title', tracking=True, required=True)
    project=fields.Char(string='Project', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    responsible_id = fields.Many2one('res.users', string='Responsible', tracking=True, default=lambda self: self.env.user, domain="[('share', '=', False), ('company_ids', 'in', company_id)]")
    team_employee_ids = fields.One2many('vehicle.teams.line','team_id', string="Employee")

class VehicleTeamsLine(models.Model):
    _name = 'vehicle.teams.line'
    _description = "Vehicle Teams Line"
    _rec_name = 'employee_id'

    employee_id=fields.Many2one('hr.employee',string="Name")
    emp_designation=fields.Char(related='employee_id.job_title',string="Designation")
    team_id=fields.Many2one('vehicle.teams', string='Team Id')


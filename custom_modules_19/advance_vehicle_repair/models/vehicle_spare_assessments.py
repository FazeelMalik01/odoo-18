from odoo import fields, models, api

class VehiclePartsAssessments(models.Model):
    _name = 'vehicle.parts.assessments'
    _description = "Vehicle Spare Parts Assessments"

    name = fields.Char(string="Assessments", required=True)

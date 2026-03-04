from odoo import models, fields, api

class SelectInspectorWizard(models.TransientModel):
    _name = 'select.inspector.wizard'
    _description = 'Select Inspector Wizard'

    jobcard_id = fields.Many2one('vehicle.jobcard', required=True)
    inspector_id = fields.Many2one('hr.employee', string="Select Inspector", required=True)

    def action_confirm(self):
        self.ensure_one()
        self.jobcard_id.inspector_id = self.inspector_id.id
        self.jobcard_id.button_quality_check()

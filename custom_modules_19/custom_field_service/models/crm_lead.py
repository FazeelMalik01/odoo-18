from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = "crm.lead"

    gps = fields.Char(string="GPS")
    fiver = fields.Char(string="Fiver Meter")
    poles = fields.Char(string="Poles")

    hide_service_fields = fields.Boolean(
        string="Hide Service Fields",
        compute="_compute_hide_service_fields"
    )

    @api.depends('stage_id')
    def _compute_hide_service_fields(self):
        for lead in self:
            # True if fields should be invisible
            lead.hide_service_fields = lead.stage_id.name == 'Lead'

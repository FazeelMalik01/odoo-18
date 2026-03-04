# -*- coding: utf-8 -*-
from odoo import models, api, _


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        for ticket in tickets:
            # Automatically create FSM task if team has FSM enabled
            if ticket.team_id and ticket.team_id.use_fsm and ticket.team_id.fsm_project_id:
                # Ensure partner exists
                if not ticket.partner_id and (ticket.partner_name or ticket.partner_email):
                    partner = ticket._partner_find_from_emails_single([ticket.partner_email])
                    if partner:
                        ticket.partner_id = partner.id
                
                # Create FSM task automatically (partner is required for FSM tasks)
                if ticket.partner_id and ticket.team_id.fsm_project_id:
                    task_vals = {
                        'name': ticket.name,
                        'helpdesk_ticket_id': ticket.id,
                        'project_id': ticket.team_id.fsm_project_id.id,
                        'partner_id': ticket.partner_id.id,
                        'description': ticket.description or '',
                    }
                    task = self.env['project.task'].create(task_vals)
                    ticket.message_post_with_source(
                        'helpdesk.ticket_conversion_link',
                        render_values={'created_record': task, 'message': _('Task automatically created')},
                        subtype_xmlid='mail.mt_note',
                    )
        return tickets

    def action_print_pdf(self):
        return self.env.ref("custom_field_service.action_ticket_report_pdf").report_action(self)
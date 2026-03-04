# -*- coding: utf-8 -*-
from odoo import models, fields, api
from collections import defaultdict


class PartnerReporting(models.TransientModel):
    _name = 'laundry.partner.reporting'
    _description = 'Partner Service Request Reporting'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    total_requests = fields.Integer(string='Total Requests', compute='_compute_statistics', store=False)
    confirmed_requests = fields.Integer(string='Confirmed Requests', compute='_compute_statistics', store=False)
    completed_requests = fields.Integer(string='Completed Requests', compute='_compute_statistics', store=False)
    delivery_requests = fields.Integer(string='Delivery Requests', compute='_compute_statistics', store=False)
    cancelled_requests = fields.Integer(string='Cancelled Requests', compute='_compute_statistics', store=False)
    pending_requests = fields.Integer(string='Pending Requests', compute='_compute_statistics', store=False)
    in_progress_requests = fields.Integer(string='In Progress Requests', compute='_compute_statistics', store=False)
    pickup_requests = fields.Integer(string='Pickup Requests', compute='_compute_statistics', store=False)
    
    @api.depends('partner_id')
    def _compute_statistics(self):
        """Compute statistics for each partner"""
        Appointment = self.env['laundry.appointment']
        for record in self:
            if not record.partner_id:
                record.total_requests = 0
                record.confirmed_requests = 0
                record.completed_requests = 0
                record.delivery_requests = 0
                record.cancelled_requests = 0
                record.pending_requests = 0
                record.in_progress_requests = 0
                record.pickup_requests = 0
                continue
            
            # Get all appointments assigned to this partner
            appointments = Appointment.search([
                ('assigned_partner_id', '=', record.partner_id.id)
            ])
            
            record.total_requests = len(appointments)
            record.confirmed_requests = len(appointments.filtered(lambda a: a.status == 'confirmed'))
            record.completed_requests = len(appointments.filtered(lambda a: a.status == 'completed'))
            record.delivery_requests = len(appointments.filtered(lambda a: a.status == 'delivery'))
            record.cancelled_requests = len(appointments.filtered(lambda a: a.status == 'cancelled'))
            record.pending_requests = len(appointments.filtered(lambda a: a.status == 'pending'))
            record.in_progress_requests = len(appointments.filtered(lambda a: a.status == 'in_progress'))
            record.pickup_requests = len(appointments.filtered(lambda a: a.status == 'pickup'))


class PartnerReportingWizard(models.TransientModel):
    _name = 'laundry.partner.reporting.wizard'
    _description = 'Partner Reporting Wizard'

    @api.model
    def get_partner_statistics(self):
        """Get statistics for all partners"""
        Appointment = self.env['laundry.appointment']
        Partner = self.env['res.partner']
        
        # Get all partners who have been assigned to appointments
        appointments = Appointment.search([
            ('assigned_partner_id', '!=', False)
        ])
        
        # Group by partner
        partner_stats = defaultdict(lambda: {
            'total': 0,
            'confirmed': 0,
            'completed': 0,
            'delivery': 0,
            'cancelled': 0,
            'pending': 0,
            'in_progress': 0,
            'pickup': 0
        })
        
        for appointment in appointments:
            partner = appointment.assigned_partner_id
            partner_stats[partner.id]['total'] += 1
            partner_stats[partner.id][appointment.status] = partner_stats[partner.id].get(appointment.status, 0) + 1
        
        # Format results
        results = []
        for partner_id, stats in partner_stats.items():
            partner = Partner.browse(partner_id)
            results.append({
                'partner_id': partner_id,
                'partner_name': partner.name,
                'total': stats['total'],
                'confirmed': stats.get('confirmed', 0),
                'completed': stats.get('completed', 0),
                'delivery': stats.get('delivery', 0),
                'cancelled': stats.get('cancelled', 0),
                'pending': stats.get('pending', 0),
                'in_progress': stats.get('in_progress', 0),
                'pickup': stats.get('pickup', 0),
            })
        
        # Sort by total requests descending
        results.sort(key=lambda x: x['total'], reverse=True)
        return results


# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CustomWorksheet(models.Model):
    _name = 'custom.worksheet'
    _description = 'Custom Worksheet'
    _order = 'create_date desc'

    name = fields.Char(string='Name', required=True, default='New')
    
    # Sample fields (all optional)
    field_one = fields.Char(string='Field One', required=False)
    field_two = fields.Char(string='Field Two', required=False)
    field_three = fields.Char(string='Field Three', required=False)
    field_four = fields.Char(string='Field Four', required=False)
    field_five = fields.Char(string='Field Five', required=False)
    field_six = fields.Char(string='Field Six', required=False)
    
    # Quality check related
    quality_point_id = fields.Many2one(
        'quality.point',
        string='Quality Point',
        compute='_compute_quality_point_id',
        store=False
    )
    quality_check_count = fields.Integer(
        string='Quality Checks',
        compute='_compute_quality_check_count',
        store=False
    )
    
    # Comments
    comments = fields.Html(string='Comments')
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(string='Active', default=True)

    def _compute_quality_point_id(self):
        for worksheet in self:
            quality_point = False
            if worksheet._origin and worksheet._origin.id:
                # Find quality point that has this worksheet linked via custom_worksheet_id
                quality_point = self.env['quality.point'].search([
                    ('custom_worksheet_id', '=', worksheet._origin.id),
                    ('service', '=', True)
                ], limit=1)
            worksheet.quality_point_id = quality_point.id if quality_point else False

    def _compute_quality_check_count(self):
        for worksheet in self:
            count = 0
            # Find ALL quality points linked to this worksheet
            if worksheet._origin and worksheet._origin.id:
                quality_points = self.env['quality.point'].search([
                    ('custom_worksheet_id', '=', worksheet._origin.id),
                    ('service', '=', True)
                ])
                if quality_points:
                    count = self.env['quality.check'].search_count([
                        ('point_id', 'in', quality_points.ids)
                    ])
            worksheet.quality_check_count = count

    def action_quality_checks_wizard(self):
        """Header button - always opens the wizard dialog with pending checks"""
        self.ensure_one()
        # Find ALL quality points linked to this worksheet (not just one)
        quality_points = self.env['quality.point'].search([
            ('custom_worksheet_id', '=', self.id),
            ('service', '=', True)
        ])
        
        if not quality_points:
            return False
        
        # Get or create quality checks for all quality points
        pending_checks = self.env['quality.check']
        for quality_point in quality_points:
            # Get pending quality checks for this quality point (state = 'none')
            existing_pending = self.env['quality.check'].search([
                ('point_id', '=', quality_point.id),
                ('quality_state', '=', 'none')
            ])
            
            # Create quality check if no pending checks exist (for service-based quality points)
            if not existing_pending:
                # Create a new quality check for this worksheet's quality point
                check = self.env['quality.check'].create({
                    'point_id': quality_point.id,
                    'team_id': quality_point.team_id.id,
                    'company_id': self.company_id.id,
                    'measure_on': 'operation',  # For service-based checks, use operation level
                })
                existing_pending = check
            
            pending_checks |= existing_pending
        
        if pending_checks:
            # Open quality check wizard dialog - will show all pending checks sequentially
            return pending_checks.action_open_quality_check_wizard()
        else:
            return False
    
    def action_view_quality_checks(self):
        """Smart button - always opens the list view"""
        self.ensure_one()
        # Find ALL quality points linked to this worksheet
        quality_points = self.env['quality.point'].search([
            ('custom_worksheet_id', '=', self.id),
            ('service', '=', True)
        ])
        
        if not quality_points:
            return False
        
        # Always show the list view
        return {
            'name': 'Quality Checks',
            'type': 'ir.actions.act_window',
            'res_model': 'quality.check',
            'view_mode': 'list,form',
            'domain': [('point_id', 'in', quality_points.ids)],
            'context': {'default_point_id': quality_points[0].id if quality_points else False},
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New'  or not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.worksheet') or 'New'
        return super().create(vals_list)

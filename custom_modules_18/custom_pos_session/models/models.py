# -*- coding: utf-8 -*-

import logging
from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'
    
    opening_employee_id = fields.Many2one(
        'hr.employee',
        string='Opening Employee',
        help='Employee who opened this session',
        readonly=True
    )
    
    closing_employee_id = fields.Many2one(
        'hr.employee',
        string='Closing Employee',
        help='Employee who closed this session',
        readonly=True
    )
    
    def write(self, vals):
        """Override write to capture opening employee when session state changes to 'opened'"""
        # Check if state is being set to 'opened' and we don't have opening_employee_id yet
        if 'state' in vals and vals['state'] == 'opened' and not self.opening_employee_id:
            # Try to get employee from various sources
            employee_id = False
            
            # Check if employee_id is in vals (might be set when opening)
            if 'employee_id' in vals and vals['employee_id']:
                employee_id = vals['employee_id']
            # Check context
            elif self.env.context.get('employee_id'):
                employee_id = self.env.context.get('employee_id')
            # Check if session already has employee_id (after write, so use recordset)
            elif hasattr(self, 'employee_id') and self.employee_id:
                employee_id = self.employee_id.id
            
            # Also check if employee_id field exists and was set in a previous write
            # Read the current employee_id from the database after the write
            if not employee_id:
                # We need to check after write, so we'll do it in a different way
                # Actually, let's try to get it from the first order if available
                first_order = self.env['pos.order'].search([('session_id', '=', self.id)], limit=1, order='id asc')
                if first_order and hasattr(first_order, 'employee_id') and first_order.employee_id:
                    employee_id = first_order.employee_id.id
                    _logger.info(f"POS Session - Found opening employee from first order: {employee_id}")
            
            if employee_id:
                vals['opening_employee_id'] = employee_id
                _logger.info(f"POS Session - Captured opening employee_id: {employee_id} when state changed to opened")
        
        result = super().write(vals)
        
        # After write, check if we need to set opening_employee_id from the session's employee_id or first order
        if 'state' in vals and vals['state'] == 'opened':
            for session in self:
                if not session.opening_employee_id:
                    employee_id = False
                    
                    # First try: Check if session has employee_id field
                    if hasattr(session, 'employee_id') and session.employee_id:
                        employee_id = session.employee_id.id
                        _logger.info(f"POS Session - Found employee_id on session: {employee_id}")
                    
                    # Second try: Get from first order created in this session
                    if not employee_id:
                        first_order = self.env['pos.order'].search([
                            ('session_id', '=', session.id)
                        ], limit=1, order='id asc')
                        if first_order and hasattr(first_order, 'employee_id') and first_order.employee_id:
                            employee_id = first_order.employee_id.id
                            _logger.info(f"POS Session - Found opening employee from first order: {employee_id}")
                    
                    if employee_id:
                        # Use sudo to bypass any access rights
                        session.sudo().write({'opening_employee_id': employee_id})
                        _logger.info(f"POS Session - Set opening_employee_id: {employee_id}")
        
        return result
    
    def action_pos_session_open(self):
        """Override to store the employee who opens the session"""
        # Get the current employee from the context or pos config
        employee_id = False
        if self.env.context.get('employee_id'):
            employee_id = self.env.context.get('employee_id')
        elif hasattr(self, 'employee_id') and self.employee_id:
            employee_id = self.employee_id.id
        
        result = super().action_pos_session_open()
        
        # Store the opening employee if we don't have it yet
        if not self.opening_employee_id and employee_id:
            self.write({'opening_employee_id': employee_id})
        
        return result
    
    def close_session_from_ui(self, bank_payment_method_diff_pairs=None):
        """Override to store the employee who closes the session from POS UI"""
        # Store closing employee before closing
        # Get employee from context (passed from POS interface)
        employee_id = False
        if self.env.context.get('employee_id'):
            employee_id = self.env.context.get('employee_id')
        elif hasattr(self, 'employee_id') and self.employee_id:
            employee_id = self.employee_id.id
        
        # Store the closing employee before calling super
        if employee_id:
            self.write({'closing_employee_id': employee_id})
        
        return super().close_session_from_ui(bank_payment_method_diff_pairs)


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        """Extend get_sale_details to add opened_by and closed_by information"""
        result = super().get_sale_details(date_start, date_stop, config_ids, session_ids, **kwargs)
        
        # Get session information for opened_by and closed_by
        if session_ids:
            sessions = self.env['pos.session'].browse(session_ids)
            if len(sessions) == 1:
                session = sessions[0]
                
                # Opened by - use the stored opening employee, fallback to first order's employee
                opened_by_employee_name = False
                if hasattr(session, 'opening_employee_id') and session.opening_employee_id:
                    opened_by_employee_name = session.opening_employee_id.name
                    _logger.info(f"POS Session Debug - opened_by from opening_employee_id: {opened_by_employee_name}")
                
                # Fallback: Get from first order's employee (more reliable for POS sessions)
                if not opened_by_employee_name:
                    first_order = self.env['pos.order'].search([
                        ('session_id', '=', session.id)
                    ], limit=1, order='id asc')
                    if first_order and hasattr(first_order, 'employee_id') and first_order.employee_id:
                        opened_by_employee_name = first_order.employee_id.name
                        _logger.info(f"POS Session Debug - opened_by from first order employee: {opened_by_employee_name}")
                
                # Final fallback: user who created the session
                if not opened_by_employee_name:
                    opened_by_user = session.create_uid
                    if opened_by_user:
                        opened_by_employee = self.env['hr.employee'].search([('user_id', '=', opened_by_user.id)], limit=1)
                        opened_by_employee_name = opened_by_employee.name if opened_by_employee else opened_by_user.name
                        _logger.info(f"POS Session Debug - opened_by from create_uid fallback: {opened_by_employee_name}")
                
                result['opened_by'] = opened_by_employee_name if opened_by_employee_name else False
                
                # Closed by - use the stored closing employee, fallback to write_uid
                if session.state == 'closed':
                    if hasattr(session, 'closing_employee_id') and session.closing_employee_id:
                        result['closed_by'] = session.closing_employee_id.name
                        _logger.info(f"POS Session Debug - closed_by from closing_employee_id: {result['closed_by']}")
                    else:
                        # Fallback to user who last modified the session
                        closed_by_user = session.write_uid
                        if closed_by_user:
                            closed_by_employee = self.env['hr.employee'].search([('user_id', '=', closed_by_user.id)], limit=1)
                            result['closed_by'] = closed_by_employee.name if closed_by_employee else closed_by_user.name
                            _logger.info(f"POS Session Debug - closed_by from write_uid fallback: {result['closed_by']}")
                        else:
                            result['closed_by'] = False
                else:
                    result['closed_by'] = False
            else:
                result['opened_by'] = False
                result['closed_by'] = False
        else:
            result['opened_by'] = False
            result['closed_by'] = False
        
        return result


# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-validate payments when invoice is fully paid"""
        payments = super(AccountPayment, self).create(vals_list)
        
        for payment in payments:
            # Only process payments related to invoices
            if payment.payment_type == 'inbound' and payment.state == 'draft':
                # Check if payment is for invoices
                invoice_ids = payment._get_invoices()
                if invoice_ids:
                    # Auto-post the payment if it's from portal
                    try:
                        if payment._context.get('from_portal', False) or \
                           (hasattr(payment, 'is_portal_payment') and payment.is_portal_payment):
                            payment.action_post()
                            _logger.info(f"Auto-posted payment {payment.name} from portal")
                            
                            # Auto-reconcile if invoice is fully paid
                            payment._auto_reconcile_invoices()
                    except Exception as e:
                        _logger.error(f"Error auto-posting payment {payment.name}: {e}")
        
        return payments

    def action_post(self):
        """Override action_post to auto-reconcile invoices when fully paid"""
        result = super(AccountPayment, self).action_post()
        
        # Auto-reconcile invoices if fully paid
        for payment in self:
            if payment.payment_type == 'inbound':
                payment._auto_reconcile_invoices()
        
        return result

    def _auto_reconcile_invoices(self):
        """Automatically reconcile payments with invoices when invoice is fully paid"""
        for payment in self:
            invoice_ids = payment._get_invoices()
            if not invoice_ids:
                continue
            
            for invoice in invoice_ids:
                # Check if invoice is fully paid
                if invoice.amount_residual <= 0.01:  # Small tolerance for rounding
                    # Find and reconcile payment with invoice
                    try:
                        # Get the payment lines
                        payment_lines = payment.line_ids.filtered(
                            lambda l: l.account_id == invoice.line_ids.mapped('account_id') and 
                            l.reconciled == False
                        )
                        
                        invoice_lines = invoice.line_ids.filtered(
                            lambda l: l.account_id == payment_lines[0].account_id if payment_lines else False and
                            l.reconciled == False
                        )
                        
                        if payment_lines and invoice_lines:
                            # Reconcile the lines
                            (payment_lines + invoice_lines).reconcile()
                            _logger.info(f"Auto-reconciled payment {payment.name} with invoice {invoice.name}")
                            
                            # Update invoice status if fully paid
                            if invoice.amount_residual <= 0.01:
                                invoice._compute_amount()
                                if invoice.amount_residual <= 0.01:
                                    # Invoice is fully paid, ensure it shows as Paid
                                    invoice._check_payment_state()
                    except Exception as e:
                        _logger.error(f"Error auto-reconciling payment {payment.name} with invoice {invoice.name}: {e}")

    def _get_invoices(self):
        """Get invoices related to this payment"""
        self.ensure_one()
        invoice_ids = self.env['account.move']
        
        if self.invoice_ids:
            invoice_ids |= self.invoice_ids
        elif self.reconciled_invoice_ids:
            invoice_ids |= self.reconciled_invoice_ids
        
        return invoice_ids


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _check_payment_state(self):
        """Override to ensure invoice shows as Paid when fully paid"""
        for invoice in self:
            if invoice.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                # Recompute payment state
                invoice._compute_amount()
                
                # If fully paid, set payment state to paid
                if invoice.amount_residual <= 0.01:
                    invoice.payment_state = 'paid'
                    _logger.info(f"Updated invoice {invoice.name} payment state to Paid")

    def action_invoice_register_payment(self):
        """Override to auto-validate payment when created from portal"""
        action = super(AccountMove, self).action_invoice_register_payment()
        
        # If called from portal, mark context
        if self._context.get('from_portal', False):
            action['context'].update({
                'from_portal': True,
                'default_payment_type': 'inbound' if self.move_type in ('out_invoice', 'out_refund') else 'outbound',
            })
        
        return action

    def action_create_work_order(self):
        """Create Work Orders from invoice - similar to sale order functionality"""
        self.ensure_one()

        if self.move_type != 'out_invoice':
            raise UserError("Work Orders can only be created from Customer Invoices.")

        # Get related sale order from invoice lines
        sale_orders = self.invoice_line_ids.mapped('sale_line_ids.order_id')
        if not sale_orders:
            raise UserError(
                "No Sale Order found for this Invoice. Work Orders can only be created from invoices linked to Sale Orders.")

        # Get service requests from sale orders
        service_requests = self.env['service.request'].search([
            ('sale_order_id', 'in', sale_orders.ids)
        ])

        if not service_requests:
            raise UserError("No Service Requests found for the related Sale Order(s).")

        Task = self.env['project.task'].sudo()
        created_tasks = self.env['project.task']

        for sr in service_requests:
            # Prevent duplicates
            existing = Task.search([('service_request_id', '=', sr.id)], limit=1)
            if existing:
                # Update existing task with paid status
                existing.write({
                    'deposit_status': 'paid',
                    'gating_status': 'completed',
                })
                created_tasks |= existing
                continue

            # Get the related sale order for this service request
            sale_order = sr.sale_order_id

            task = Task.create({
                'name': f"{sr.name or 'Service Request'} - {sr.customer_id.name}",
                'service_request_id': sr.id,
                'sale_order_id': sale_order.id if sale_order else False,
                'estimate_id': sale_order.id if sale_order else False,

                # deposit and gating status automatically
                'deposit_status': 'paid',  # Automatically set to Paid
                'gating_status': 'completed',  # Automatically set to Completed

                # Patch default project.task fields
                'partner_id': sr.customer_id.id,
                'partner_phone': sr.primary_phone,
                'date_deadline': sr.requested_appointment,
            })

            created_tasks |= task
            _logger.info("Created Work Order %s for Service Request %s from Invoice %s", task.id, sr.id, self.name)

        if not created_tasks:
            raise UserError("No Work Orders were created. All Service Requests may already have Work Orders.")

        # Open the first task
        return {
            'name': "Work Order",
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': created_tasks[0].id,
            'target': 'current',
        }


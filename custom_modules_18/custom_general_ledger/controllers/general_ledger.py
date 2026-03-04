from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
import json


class GeneralLedgerController(http.Controller):

    @http.route('/general_ledger/data', type='json', auth='user')
    def get_general_ledger_data(self, start_date=None, end_date=None, project_id=None, partner_id=None):
        domain = []

        # Add date filters if provided
        if start_date and end_date:
            domain.append(('date', '>=', start_date))
            domain.append(('date', '<=', end_date))

        # Add project filter if provided
        if project_id:
            domain.append(('analytic_account_id', '=', int(project_id)))

        # Add partner filter if provided
        if partner_id:
            domain.append(('partner_id', '=', int(partner_id)))

        # Fetch journal items with proper ordering
        records = request.env['account.move.line'].search(
            domain,
            limit=50,
            order="date asc, id asc"
        )

        running_balance = 0
        data = []

        for rec in records:
            running_balance += rec.debit - rec.credit

            # Try to find related sale.order via invoice_origin
            sale_order = None
            if rec.move_id and rec.move_id.invoice_origin:
                sale_order = request.env['sale.order'].search(
                    [('name', '=', rec.move_id.invoice_origin)],
                    limit=1
                )

            vendor_name = sale_order.vendor_id.display_name if sale_order and sale_order.vendor_id else "—"

            data.append({
                'id': rec.id,
                'date': rec.date.strftime("%Y-%m-%d") if rec.date else "",
                'communication': rec.ref or rec.name or "",
                'partner': rec.partner_id.display_name or "",
                'vendor': vendor_name,
                'project': rec.analytic_account_id.display_name if rec.analytic_account_id else "",
                'debit': rec.debit,
                'credit': rec.credit,
                'balance': running_balance,
            })

        return data

    # Add a method to be called when invoices are posted
    @http.route('/general_ledger/invoice_posted', type='json', auth='user')
    def invoice_posted_notification(self, invoice_id):
        """Called when an invoice is posted to refresh the ledger"""
        invoice = request.env['account.move'].browse(invoice_id)
        if invoice.exists() and invoice.move_type == 'out_invoice':
            # You can trigger a refresh or return updated data
            return {'success': True, 'message': 'Invoice posted, ledger should refresh'}
        return {'success': False, 'message': 'Invalid invoice'}
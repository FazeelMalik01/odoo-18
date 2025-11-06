from odoo import http
from odoo.http import request

class CustomReportController(http.Controller):

    @http.route(['/public/invoice/pdf/<int:invoice_id>'], type='http', auth="public", website=True, csrf=False)
    def custom_invoice_pdf(self, invoice_id, **kw):
        # Fetch invoice with sudo
        invoice = request.env['account.move'].sudo().browse(invoice_id)
        if not invoice or not invoice.exists():
            return request.not_found()

        if invoice.move_type != 'out_invoice':
            return request.not_found()

        # Render report with sudo
        report_name = "custom_invoice_report.peptidat_invoice_report"
        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            report_name, [invoice.id]
        )

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', f'inline; filename="Invoice_{invoice.name}.pdf"'),
        ]
        return request.make_response(pdf_content, headers=pdfhttpheaders)

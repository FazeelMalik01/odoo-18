# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging
import base64

_logger = logging.getLogger(__name__)


class CustomPosReceipt(http.Controller):
    @http.route('/custom_pos_receipt/generate_html', type='http', auth='user', methods=['POST'], csrf=False)
    def generate_html_report(self, **kwargs):
        """Generate HTML report for POS order"""
        try:
            _logger.info("Custom HTML generation request received")
            
            # Get data from request
            if request.httprequest.data:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            else:
                data = request.params
            
            order_id = data.get('order_id')
            pos_config_id = data.get('pos_config_id')
            report_type = data.get('report_type', 'standard')
            _logger.info(f"Order ID received: {order_id}, POS Config ID: {pos_config_id}, Report Type: {report_type}")
            
            if not order_id:
                return request.make_json_response({'error': 'Order ID is required'}, status=400)
            
            # Get the POS order
            order = request.env['pos.order'].browse(int(order_id))
            if not order.exists():
                return request.make_json_response({'error': 'Order not found'}, status=404)
            
            _logger.info(f"Order found: {order.name}")
            
            # Get receipt type from POS configuration
            if pos_config_id:
                pos_config = request.env['pos.config'].browse(int(pos_config_id))
                if pos_config.exists():
                    report_type = pos_config.receipt_type
                    _logger.info(f"Using receipt type from POS config: {report_type}")
                else:
                    _logger.warning(f"POS config {pos_config_id} not found, using default")
            else:
                # Fallback to order's POS config
                if order.config_id:
                    report_type = order.config_id.receipt_type
                    _logger.info(f"Using receipt type from order's POS config: {report_type}")
                else:
                    _logger.warning("No POS config found, using default")
            
            # Generate HTML report using direct template rendering
            try:
                # Select report based on report_type
                if report_type == 'doha':
                    report_ref = "custom_pos_receipt.action_pos_order_report_doha"
                    report = request.env.ref("custom_pos_receipt.action_pos_order_report_doha")
                    _logger.info("Using Doha report template")
                elif report_type == 'icity':
                    report_ref = "custom_pos_receipt.action_pos_order_report"
                    report = request.env.ref("custom_pos_receipt.action_pos_order_report")
                    _logger.info("Using iCity report template")
                else:
                    # Default to doha if unknown type
                    report_ref = "custom_pos_receipt.action_pos_order_report_doha"
                    report = request.env.ref("custom_pos_receipt.action_pos_order_report_doha")
                    _logger.info("Using default Doha report template")
                
                # Prepare context data with partner information from the order
                context_data = {}
                if order.partner_id:
                    context_data['selected_partner'] = order.partner_id
                    _logger.info(f"Order partner: {order.partner_id.name}")
                
                html_content, _ = report._render_qweb_html(
                    report_ref,                                   # report_ref
                    [order.id],                                   # docids
                    context_data                                   # data
                )
                
                _logger.info(f"HTML content generated, size: {len(html_content)} bytes")
                
            except Exception as e:
                _logger.error(f"Error in HTML generation: {str(e)}", exc_info=True)
                return request.make_json_response({'error': f'HTML generation failed: {str(e)}'}, status=500)
            
            _logger.info("HTML generated successfully")
            
            return request.make_json_response({
                'success': True,
                'html_content': html_content.decode('utf-8'),
                'filename': f'pos_receipt_{order.name}.html'
            })
            
        except Exception as e:
            _logger.error(f"Error generating HTML: {str(e)}", exc_info=True)
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route('/custom_pos_receipt/generate_pdf', type='http', auth='user', methods=['POST'], csrf=False)
    def generate_pdf_report(self, **kwargs):
        """Generate PDF report for POS order"""
        try:
            _logger.info("Custom PDF generation request received")
            
            # Get data from request
            if request.httprequest.data:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            else:
                data = request.params
            
            order_id = data.get('order_id')
            pos_config_id = data.get('pos_config_id')
            report_type = data.get('report_type', 'standard')
            _logger.info(f"Order ID received: {order_id}, POS Config ID: {pos_config_id}, Report Type: {report_type}")
            
            if not order_id:
                return request.make_json_response({'error': 'Order ID is required'}, status=400)
            
            # Get the POS order
            order = request.env['pos.order'].browse(int(order_id))
            if not order.exists():
                return request.make_json_response({'error': 'Order not found'}, status=404)
            
            _logger.info(f"Order found: {order.name}")
            
            # Get receipt type from POS configuration
            if pos_config_id:
                pos_config = request.env['pos.config'].browse(int(pos_config_id))
                if pos_config.exists():
                    report_type = pos_config.receipt_type
                    _logger.info(f"Using receipt type from POS config: {report_type}")
                else:
                    _logger.warning(f"POS config {pos_config_id} not found, using default")
            else:
                # Fallback to order's POS config
                if order.config_id:
                    report_type = order.config_id.receipt_type
                    _logger.info(f"Using receipt type from order's POS config: {report_type}")
                else:
                    _logger.warning("No POS config found, using default")
            
            # Generate PDF report using Odoo's report system
            try:
                # Select report based on report_type
                if report_type == 'doha':
                    report_ref = "custom_pos_receipt.action_pos_order_report_doha"
                    report = request.env.ref("custom_pos_receipt.action_pos_order_report_doha")
                    _logger.info("Using Doha report template")
                elif report_type == 'icity':
                    report_ref = "custom_pos_receipt.action_pos_order_report"
                    report = request.env.ref("custom_pos_receipt.action_pos_order_report")
                    _logger.info("Using iCity report template")
                else:
                    # Default to doha if unknown type
                    report_ref = "custom_pos_receipt.action_pos_order_report_doha"
                    report = request.env.ref("custom_pos_receipt.action_pos_order_report_doha")
                    _logger.info("Using default Doha report template")
                
                # Prepare context data with partner information from the order
                context_data = {}
                if order.partner_id:
                    context_data['selected_partner'] = order.partner_id
                    _logger.info(f"Order partner: {order.partner_id.name}")
                
                # Generate PDF
                pdf_content, _ = report._render_qweb_pdf(
                    report_ref,                                   # report_ref
                    [order.id],                                   # docids
                    context_data                                   # data
                )
                
                _logger.info(f"PDF content generated, size: {len(pdf_content)} bytes")
                
            except Exception as e:
                _logger.error(f"Error in PDF generation: {str(e)}", exc_info=True)
                return request.make_json_response({'error': f'PDF generation failed: {str(e)}'}, status=500)
            
            _logger.info("PDF generated successfully")
            
            return request.make_json_response({
                'success': True,
                'pdf_content': base64.b64encode(pdf_content).decode('utf-8'),
                'filename': f'pos_receipt_{order.name}.pdf'
            })
            
        except Exception as e:
            _logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
            return request.make_json_response({'error': str(e)}, status=500)

    @http.route('/custom_pos_receipt/get_receipt_type', type='http', auth='user', methods=['GET'], csrf=False)
    def get_receipt_type(self, **kwargs):
        """Get the receipt type from POS configuration"""
        try:
            pos_config_id = request.params.get('pos_config_id')
            
            if pos_config_id:
                pos_config = request.env['pos.config'].browse(int(pos_config_id))
                if pos_config.exists():
                    receipt_type = pos_config.receipt_type
                    _logger.info(f"Receipt type for POS config {pos_config_id}: {receipt_type}")
                else:
                    receipt_type = 'doha'  # Default fallback
                    _logger.warning(f"POS config {pos_config_id} not found, using default")
            else:
                # Fallback to global parameter if no POS config specified
                receipt_type = request.env['ir.config_parameter'].sudo().get_param('custom_pos_receipt.pos_receipt_type', 'doha')
                _logger.info(f"Using global receipt type: {receipt_type}")
            
            return request.make_json_response({
                'success': True,
                'receipt_type': receipt_type
            })
            
        except Exception as e:
            _logger.error(f"Error getting receipt type: {str(e)}", exc_info=True)
            return request.make_json_response({
                'success': False,
                'receipt_type': 'doha',  # Default fallback
                'error': str(e)
            }, status=500)


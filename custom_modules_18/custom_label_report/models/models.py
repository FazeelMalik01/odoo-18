# -*- coding: utf-8 -*-

from odoo import models


class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    def _prepare_report_data(self):
        xml_id, data = super()._prepare_report_data()
        
        # Override: Always use product barcode instead of lot/serial numbers
        if data.get('custom_barcodes'):
            # Replace lot/serial barcodes with product barcodes
            custom_barcodes = {}
            for product_id, barcode_list in data['custom_barcodes'].items():
                product = self.env['product.product'].browse(int(product_id))
                if product.barcode:
                    # Use product barcode instead of lot/serial numbers
                    # Sum up the quantities for all lots/serials
                    total_qty = sum(qty for _, qty in barcode_list)
                    custom_barcodes[product_id] = [(product.barcode, total_qty)]
                # If no product barcode, don't add to custom_barcodes (will show nothing)
            data['custom_barcodes'] = custom_barcodes
        
        return xml_id, data

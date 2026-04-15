from odoo import models, fields, api
import logging
import requests

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    webflow_item_id = fields.Char("Webflow Item ID")
    webflow_category = fields.Many2one("product.category", "Webflow Category")
    pdf_url = fields.Char("PDF URL")
    website_url = fields.Char("Website URL")
    pick_up_price = fields.Float("Pick-Up Price")
    drop_off_price = fields.Float("Drop-Off Price")
    webflow_last_qty = fields.Float("Last Synced Forecast Qty")
    collection_id = fields.Char("Collection ID")
    locale_id = fields.Char("Locale ID")
    catalog_id = fields.Char("Catalog ID")
    location_id = fields.Char("Location ID")
    webflow_collection_id = fields.Char("Webflow Collection ID")  # NEW FIELD
    webflow_gallery_urls = fields.Text("Gallery Image URLs JSON")
    webflow_product_img_url = fields.Char("Webflow Main Image URL")
    webflow_line_item_ids = fields.One2many(
        "webflow.line.item", "product_tmpl_id", string="Webflow Line Items"
    )
 
class ProductProduct(models.Model):
    _inherit = "product.product"

    def _push_forecast_to_webflow(self):

        token = "aa9c58d2fb30a77bec00a549d956035fccbe271e466be7f625b99148c1d0d1b2"
        collection_id = "68360a7c8d2bb90e61d3883f"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        for product in self:

            tmpl = product.product_tmpl_id
            webflow_id = tmpl.webflow_item_id

            if not webflow_id:
                continue

            # VERY IMPORTANT
            product.invalidate_recordset(["virtual_available"])

            forecast_qty = float(product.virtual_available or 0)

            if tmpl.webflow_last_qty == forecast_qty:
                continue

            url = f"https://api.webflow.com/v2/collections/{collection_id}/items/{webflow_id}"

            payload = {"fieldData": {"quantity": forecast_qty}}

            try:

                response = requests.patch(
                    url, json=payload, headers=headers, timeout=30
                )

                response.raise_for_status()

                tmpl.webflow_last_qty = forecast_qty

                _logger.info(
                    "Webflow quantity synced: %s → %s", product.name, forecast_qty
                )

            except Exception as e:

                _logger.error("Webflow update failed for %s: %s", product.name, e)

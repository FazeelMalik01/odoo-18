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
    webflow_collection_id = fields.Char("Webflow Collection ID")  # NEW FIELD
    webflow_line_item_ids = fields.One2many(
        "webflow.line.item", "product_tmpl_id", string="Webflow Line Items"
    )

    def _parse_price(self, value):

        if not value:
            return False

        try:
            cleaned = str(value).replace("$", "").replace(",", "").strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return False

    def _update_stock(self, product, quantity):

        location = self.env.ref("stock.stock_location_stock")

        quant = self.env["stock.quant"].search(
            [
                ("product_id", "=", product.id),
                ("location_id", "=", location.id),
            ],
            limit=1,
        )

        if quant:
            quant.inventory_quantity = quantity
            quant.action_apply_inventory()
        else:
            self.env["stock.quant"].create(
                {
                    "product_id": product.id,
                    "location_id": location.id,
                    "inventory_quantity": quantity,
                }
            ).action_apply_inventory()

    # @api.model
    # def sync_webflow_products(self):
    #     collection_id = "68360a7c8d2bb90e61d3883f"
    #     token = "aa9c58d2fb30a77bec00a549d956035fccbe271e466be7f625b99148c1d0d1b2"
    #     base_url = f"https://api.webflow.com/v2/collections/{collection_id}/items"

    #     headers = {"Authorization": f"Bearer {token}"}

    #     items = []
    #     limit = 100
    #     offset = 0

    #     while True:
    #         url = f"{base_url}?limit={limit}&offset={offset}&live=true"
    #         _logger.info("Fetching Webflow items: %s", url)

    #         try:
    #             response = requests.get(url, headers=headers, timeout=30)
    #             response.raise_for_status()
    #             data = response.json()
    #             batch = data.get("items", [])
    #             items.extend(batch)

    #             if len(batch) < limit:
    #                 break

    #             offset += limit

    #         except requests.RequestException as e:
    #             _logger.error("Webflow Sync Failed: %s", e)
    #             return

    #     for item in items:
    #         try:
    #             field_data = item.get("fieldData", {})

    #             staffed_price = self._parse_price(
    #                 field_data.get("staffed-price-3")
    #             )
    #             pickup_price = self._parse_price(
    #                 field_data.get("pick-up-price-3")
    #             )
    #             dropoff_price = self._parse_price(
    #                 field_data.get("drop-off-price-3")
    #             )

    #             list_price = (
    #                 staffed_price
    #                 if staffed_price is not False
    #                 else pickup_price or 0.0
    #             )

    #             webflow_qty = field_data.get("quantity") or 0.0

    #             category = False
    #             category_name = field_data.get("catalog-product-name")

    #             if category_name:
    #                 category = self.env["product.category"].search(
    #                     [("name", "=", category_name)], limit=1
    #                 ) or self.env["product.category"].create(
    #                     {"name": category_name}
    #                 )

    #             vals = {
    #                 "name": field_data.get("catalog-product-name")
    #                         or field_data.get("name"),
    #                 "default_code": field_data.get("slug"),
    #                 "list_price": list_price,
    #                 "pick_up_price": pickup_price or 0.0,
    #                 "drop_off_price": dropoff_price or 0.0,
    #                 "description_sale": field_data.get(
    #                     "catalog-product-description"
    #                 ),
    #                 "pdf_url": field_data.get("single-page-pdf-url"),
    #                 "website_url": field_data.get("header-url"),
    #                 "webflow_item_id": item.get("id"),
    #                 "webflow_category": category.id if category else False,
    #                 "is_storable": True,
    #             }

    #             product = self.search(
    #                 [("webflow_item_id", "=", item.get("id"))],
    #                 limit=1,
    #             )

    #             if product:
    #                 product.write(vals)
    #             else:
    #                 product = self.create(vals)

    #             self._update_stock(product.product_variant_id, webflow_qty)

    #         except Exception as e:
    #             _logger.error(
    #                 "Failed to sync product %s: %s",
    #                 field_data.get("catalog-product-name") or item.get("id"),
    #                 e,
    #             )

    #     _logger.info("Webflow Sync Complete")
    @api.model
    def sync_webflow_products(self):

        collection_id = "68360a7c8d2bb90e61d3883f"
        token = "aa9c58d2fb30a77bec00a549d956035fccbe271e466be7f625b99148c1d0d1b2"

        base_url = f"https://api.webflow.com/v2/collections/{collection_id}/items"

        headers = {"Authorization": f"Bearer {token}"}

        items = []
        limit = 100
        offset = 0

        # ---------------- FETCH WEBFLOW ITEMS ---------------- #

        while True:

            url = f"{base_url}?limit={limit}&offset={offset}&live=true"

            _logger.info("Fetching Webflow items: %s", url)

            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()

                data = response.json()

                batch = data.get("items", [])
                items.extend(batch)

                if len(batch) < limit:
                    break

                offset += limit

            except requests.RequestException as e:

                _logger.error("Webflow Sync Failed: %s", e)
                return

        # ---------------- PROCESS ITEMS ---------------- #

        for item in items:

            try:

                field_data = item.get("fieldData", {})

                staffed_price = self._parse_price(field_data.get("staffed-price-3"))

                pickup_price = self._parse_price(field_data.get("pick-up-price-3"))

                dropoff_price = self._parse_price(field_data.get("drop-off-price-3"))

                list_price = (
                    staffed_price if staffed_price is not False else pickup_price or 0.0
                )

                webflow_qty = field_data.get("quantity") or 0.0

                # -------- CATEGORY -------- #

                category = False
                category_name = field_data.get("catalog-product-name")

                if category_name:

                    category = self.env["product.category"].search(
                        [("name", "=", category_name)],
                        limit=1,
                    ) or self.env["product.category"].create({"name": category_name})

                # -------- COLLECTION + LINE ITEMS -------- #

                webflow_collection_id = field_data.get("collection-id")
                line_items = field_data.get("line-items", [])

                # -------- PRODUCT VALUES -------- #

                vals = {
                    "name": field_data.get("catalog-product-name")
                    or field_data.get("name"),
                    "default_code": field_data.get("slug"),
                    "list_price": list_price,
                    "pick_up_price": pickup_price or 0.0,
                    "drop_off_price": dropoff_price or 0.0,
                    "description_sale": field_data.get("catalog-product-description"),
                    "pdf_url": field_data.get("single-page-pdf-url"),
                    "website_url": field_data.get("header-url"),
                    "webflow_item_id": item.get("id"),
                    "webflow_collection_id": webflow_collection_id,
                    "webflow_category": category.id if category else False,
                    "is_storable": True,
                }

                # -------- CREATE OR UPDATE PRODUCT -------- #

                product = self.search(
                    [("webflow_item_id", "=", item.get("id"))],
                    limit=1,
                )

                if product:
                    product.write(vals)
                else:
                    product = self.create(vals)

                # -------- UPDATE STOCK -------- #

                self._update_stock(product.product_variant_id, webflow_qty)

                # -------- STORE LINE ITEMS -------- #

                if line_items:

                    product.webflow_line_item_ids.unlink()

                    line_vals = []

                    for line_id in line_items:

                        line_vals.append(
                            {
                                "product_tmpl_id": product.id,
                                "line_item_id": line_id,
                            }
                        )

                    self.env["webflow.line.item"].create(line_vals)

            except Exception as e:

                _logger.error(
                    "Failed to sync product %s: %s",
                    field_data.get("catalog-product-name") or item.get("id"),
                    e,
                )

        _logger.info("Webflow Sync Complete")

    @api.model
    def sync_webflow_products_addons(self):
        collection_id = "68360a7c8d2bb90e61d387ff"
        token = "aa9c58d2fb30a77bec00a549d956035fccbe271e466be7f625b99148c1d0d1b2"
        base_url = f"https://api.webflow.com/v2/collections/{collection_id}/items"

        headers = {"Authorization": f"Bearer {token}"}

        items = []
        limit = 100
        offset = 0

        while True:
            url = f"{base_url}?limit={limit}&offset={offset}&live=true"
            _logger.info("Fetching Webflow items: %s", url)

            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()

                batch = data.get("items", [])
                items.extend(batch)

                if len(batch) < limit:
                    break

                offset += limit

            except requests.RequestException as e:
                _logger.error("Webflow Sync Failed: %s", e)
                return

        for item in items:
            try:
                field_data = item.get("fieldData", {})

                # Parse price from "base-price"
                base_price = self._parse_price(field_data.get("base-price")) or 0.0

                vals = {
                    "name": field_data.get("name"),
                    "default_code": field_data.get("slug"),
                    "list_price": base_price,
                    "description_sale": field_data.get("description"),
                    "webflow_item_id": item.get("id"),
                    "is_storable": True,
                }

                product = self.search(
                    [("webflow_item_id", "=", item.get("id"))],
                    limit=1,
                )

                if product:
                    product.write(vals)
                    _logger.info("Updated product: %s", vals["name"])
                else:
                    product = self.create(vals)
                    _logger.info("Created product: %s", vals["name"])

            except Exception as e:
                _logger.error(
                    "Failed to sync product %s: %s",
                    field_data.get("name") or item.get("id"),
                    e,
                )

        _logger.info("Webflow Sync Complete")

    @api.model
    def sync_webflow_forecasted_stock(self):
        products = self.env["product.product"].search(
            [("product_tmpl_id.webflow_item_id", "!=", False)]
        )

        products._push_forecast_to_webflow()

        _logger.info("Webflow forecast stock sync completed")


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

import base64
import logging
import requests

from odoo import models

_logger = logging.getLogger(__name__)


class WebflowAddonsSync(models.TransientModel):
    _name = 'webflow.addons.sync'
    _description = 'Webflow Addons Sync'

    def _get_credentials(self):
        ICP = self.env['ir.config_parameter'].sudo()
        token = ICP.get_param('webflow.auth_token')
        collection_id = ICP.get_param('webflow.addons_collection_id')
        return token, collection_id

    def _fetch_image_b64(self, url):
        if not url:
            return False
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return base64.b64encode(resp.content).decode('utf-8')
        except Exception as e:
            _logger.warning("Failed to fetch addon image from %s: %s", url, e)
            return False

    def sync_addons(self):
        token, collection_id = self._get_credentials()

        if not token or not collection_id:
            _logger.error(
                "[ABORT] Addons sync: auth_token or addons_collection_id not set in Settings."
            )
            return

        url = f"https://api.webflow.com/v2/collections/{collection_id}/items"
        headers = {
            "Authorization": f"Bearer {token}",
            "accept": "application/json",
        }

        all_items = []
        offset = 0
        limit = 100

        while True:
            _logger.info("[ADDONS FETCH] offset=%s limit=%s", offset, limit)
            try:
                resp = requests.get(
                    url,
                    headers=headers,
                    params={"limit": limit, "offset": offset},
                    timeout=30,
                )
                resp.raise_for_status()
            except Exception as e:
                _logger.exception("[ERROR] Webflow addons API request failed: %s", e)
                break

            payload = resp.json()
            items = payload.get("items", [])
            total = payload.get("pagination", {}).get("total", 0)

            _logger.info(
                "[ADDONS PAGE] fetched=%s cumulative=%s total=%s",
                len(items),
                len(all_items) + len(items),
                total,
            )

            all_items.extend(items)

            if not items or len(all_items) >= total:
                break

            offset += limit

        _logger.info("[ADDONS TOTAL] %s items fetched from Webflow", len(all_items))

        success = failed = 0

        for item in all_items:
            try:
                with self.env.cr.savepoint():
                    self._sync_single_addon(item, collection_id)
                    success += 1
            except Exception as e:
                failed += 1
                _logger.exception(
                    "[ERROR] Failed to sync addon %s: %s",
                    item.get("id"),
                    e,
                )

        _logger.info(
            "[ADDONS DONE] success=%s failed=%s total=%s",
            success,
            failed,
            len(all_items),
        )

    def _sync_single_addon(self, item, collection_id):
        fd = item.get("fieldData", {})

        webflow_item_id = item.get("id")
        name = fd.get("full-name") or fd.get("name")

        if not name:
            _logger.warning("[ADDONS SKIP] Item %s has no name", webflow_item_id)
            return

        is_archived = item.get("isArchived", False)
        is_draft = item.get("isDraft", False)
        active = not is_archived and not is_draft

        try:
            list_price = float(fd.get("price") or 0.0)
        except (TypeError, ValueError):
            list_price = 0.0

        description_parts = []
        desc = fd.get("description")
        if desc:
            description_parts.append(desc)
        rate = fd.get("rate")
        if rate:
            description_parts.append(f"Rate: {rate}")
        alt = fd.get("webp-alt-text")
        if alt:
            description_parts.append(alt)
        description_sale = "\n\n".join(description_parts) if description_parts else False

        slug = fd.get("slug")
        website_url = False
        if slug:
            website_url = slug if str(slug).startswith("/") else f"/{slug}"

        webp = fd.get("webp") or {}
        image_url = webp.get("url")
        image_b64 = self._fetch_image_b64(image_url)

        locale_id = item.get("cmsLocaleId")

        vals = {
            "name": name,
            "active": active,
            "list_price": list_price,
            "description_sale": description_sale,
            "website_url": website_url,
            "webflow_item_id": webflow_item_id,
            "webflow_collection_id": collection_id,
            "collection_id": collection_id,
            "is_storable": True,
        }
        if locale_id:
            vals["locale_id"] = locale_id

        if image_b64:
            vals["image_1920"] = image_b64

        ProductTmpl = self.env["product.template"].sudo()
        product = ProductTmpl.search(
            [("webflow_item_id", "=", webflow_item_id)],
            limit=1,
        )

        if product:
            product.write(vals)
            _logger.info("[ADDONS UPDATE] '%s' (WF:%s)", name, webflow_item_id)
        else:
            ProductTmpl.create(vals)
            _logger.info("[ADDONS CREATE] '%s' (WF:%s)", name, webflow_item_id)

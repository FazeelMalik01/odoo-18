import base64
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from odoo import models

_logger = logging.getLogger(__name__)

# Thread-safe: no Odoo env (used for parallel image downloads).
def _http_get_image_b64(url, timeout=15):
    if not url:
        return False
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode('utf-8')
    except Exception as e:
        _logger.warning("Failed to fetch image from %s: %s", url, e)
        return False


class WebflowProductSync(models.TransientModel):
    _name = 'webflow.product.sync'
    _description = 'Webflow Product Sync'

    def _get_credentials(self):
        ICP = self.env['ir.config_parameter'].sudo()
        token = ICP.get_param('webflow.auth_token')
        collection_id = ICP.get_param('webflow.product_collection_id')
        return token, collection_id

    def _fetch_image_b64(self, url):
        return _http_get_image_b64(url)

    def _prefetch_images_parallel(self, urls):
        """Download unique image URLs concurrently (I/O bound)."""
        urls = [u for u in urls if u]
        if not urls:
            return {}
        max_workers = min(16, max(4, len(urls)))
        out = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(_http_get_image_b64, u): u for u in urls
            }
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    b64 = future.result()
                    if b64:
                        out[url] = b64
                except Exception as e:
                    _logger.warning("Image worker failed for %s: %s", url, e)
        return out

    def _index_categories_by_webflow_id(self):
        Category = self.env['product.category'].sudo()
        cats = Category.search([('webflow_category_id', '!=', False)])
        by_wf = defaultdict(list)
        for cat in cats:
            by_wf[cat.webflow_category_id].append(cat)
        return by_wf

    def _map_location_to_company(self):
        Company = self.env['res.company'].sudo()
        companies = Company.search([('webflow_location_id', '!=', False)])
        return {c.webflow_location_id: c for c in companies}

    def _default_branch_company(self, Company):
        main = Company.browse(1)
        if main:
            return main
        return self.env.company

    def sync_products(self):
        token, collection_id = self._get_credentials()

        if not token or not collection_id:
            _logger.error(
                "[ABORT] Product sync: auth_token or product_collection_id not set in Settings."
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
            _logger.info("[FETCH] offset=%s limit=%s", offset, limit)
            try:
                resp = requests.get(
                    url,
                    headers=headers,
                    params={"limit": limit, "offset": offset},
                    timeout=30,
                )
                resp.raise_for_status()
            except Exception as e:
                _logger.exception("[ERROR] Webflow API request failed: %s", e)
                break

            payload = resp.json()
            items = payload.get("items", [])
            total = payload.get("pagination", {}).get("total", 0)

            _logger.info(
                "[PAGE] fetched=%s cumulative=%s total=%s",
                len(items), len(all_items) + len(items), total
            )

            all_items.extend(items)

            if not items or len(all_items) >= total:
                break

            offset += limit

        _logger.info("[TOTAL] %s products fetched from Webflow", len(all_items))

        Company = self.env['res.company'].sudo()
        cats_by_wf_id = self._index_categories_by_webflow_id()
        company_by_location = self._map_location_to_company()
        default_company = self._default_branch_company(Company)

        image_urls = set()
        parsed_rows = []
        for item in all_items:
            row = self._parse_item_for_sync(
                item,
                cats_by_wf_id,
                company_by_location,
                default_company,
            )
            if row is None:
                continue
            parsed_rows.append(row)
            if row.get("product_img_url"):
                image_urls.add(row["product_img_url"])

        image_by_url = self._prefetch_images_parallel(image_urls)

        all_wf_ids = {r["webflow_item_id"] for r in parsed_rows}
        ProductTmpl = self.env['product.template'].sudo()
        existing_by_key = {}
        if all_wf_ids:
            for rec in ProductTmpl.search(
                [('webflow_item_id', 'in', list(all_wf_ids))]
            ):
                cid = rec.company_id.id if rec.company_id else False
                existing_by_key[(rec.webflow_item_id, cid)] = rec

        success = failed = 0
        for row in parsed_rows:
            try:
                with self.env.cr.savepoint():
                    self._apply_parsed_row(
                        row,
                        image_by_url,
                        existing_by_key,
                        ProductTmpl,
                        Company,
                    )
                success += 1
            except Exception as e:
                failed += 1
                _logger.exception(
                    "[ERROR] Failed to sync product %s: %s",
                    row.get("webflow_item_id"),
                    e,
                )

        _logger.info(
            "[DONE] Product sync complete — success=%s failed=%s total=%s",
            success, failed, len(all_items)
        )

    def _parse_item_for_sync(
        self,
        item,
        cats_by_wf_id,
        company_by_location,
        default_company,
    ):
        fd = item.get("fieldData", {})
        webflow_item_id = item.get("id")
        name = fd.get("product-full-name-pt") or fd.get("name")
        if not name:
            _logger.warning("[SKIP] Product %s has no name", webflow_item_id)
            return None

        active = fd.get("product-active", True)
        lst_price = float(fd.get("prices-01") or 0.0)
        pick_up_price = float(fd.get("prices-02") or 0.0)
        cost_price = float(fd.get("prices-03") or 0.0)

        webflow_loc_id = fd.get("location")
        if webflow_loc_id:
            location_company = company_by_location.get(webflow_loc_id) or default_company
        else:
            location_company = default_company

        raw_categories = fd.get("categories") or []
        if isinstance(raw_categories, str) and raw_categories:
            raw_categories = [raw_categories]
        elif not isinstance(raw_categories, list):
            raw_categories = []

        matched_categ_by_company = {}
        for wf_cat_id in raw_categories:
            if not wf_cat_id:
                continue
            for cat in cats_by_wf_id.get(wf_cat_id, ()):
                if not cat.company_id:
                    continue
                cid = cat.company_id.id
                if cid not in matched_categ_by_company:
                    matched_categ_by_company[cid] = cat

        target_company_ids = set(matched_categ_by_company.keys())
        target_company_ids.add(location_company.id)

        description = fd.get("product-description") or fd.get(
            "product-description-with-links"
        )
        product_img_url = (fd.get("product-img") or {}).get("url")
        gallery_urls = []
        for i in range(1, 6):
            img_obj = fd.get(f"gallery-image-0{i}") or {}
            gurl = img_obj.get("url")
            if gurl:
                gallery_urls.append(gurl)

        return {
            "webflow_item_id": webflow_item_id,
            "name": name,
            "active": active,
            "lst_price": lst_price,
            "pick_up_price": pick_up_price,
            "cost_price": cost_price,
            "description": description,
            "website_url": fd.get("category-url"),
            "product_img_url": product_img_url,
            "gallery_urls": gallery_urls,
            "matched_categ_by_company": matched_categ_by_company,
            "target_company_ids": target_company_ids,
        }

    def _apply_parsed_row(self, row, image_by_url, existing_by_key, ProductTmpl, Company):
        webflow_item_id = row["webflow_item_id"]
        name = row["name"]
        gallery_urls = row["gallery_urls"]
        cost_price = row["cost_price"]
        matched_categ_by_company = row["matched_categ_by_company"]

        image_b64 = image_by_url.get(row["product_img_url"]) if row.get(
            "product_img_url"
        ) else False

        base_vals = {
            'name': row["name"],
            'active': row["active"],
            'list_price': row["lst_price"],
            'pick_up_price': row["pick_up_price"],
            'drop_off_price': row["cost_price"],
            'description_sale': row["description"],
            'website_url': row["website_url"],
            'webflow_item_id': webflow_item_id,
            'is_storable': True,
        }
        if image_b64:
            base_vals['image_1920'] = image_b64
        if gallery_urls:
            base_vals['description_picking'] = "\n".join(gallery_urls)

        for comp in Company.browse(sorted(row["target_company_ids"])):
            vals = dict(base_vals)
            vals['company_id'] = comp.id
            matched_categ = matched_categ_by_company.get(comp.id)
            if matched_categ:
                vals['categ_id'] = matched_categ.id
                vals['webflow_category'] = matched_categ.id

            key = (webflow_item_id, comp.id)
            product = existing_by_key.get(key)
            if product:
                product.write(vals)
                _logger.debug(
                    "[UPDATE] '%s' (WF:%s) → Branch: %s",
                    name, webflow_item_id, comp.name,
                )
            else:
                product = ProductTmpl.with_company(comp).create(vals)
                existing_by_key[key] = product
                _logger.debug(
                    "[CREATE] '%s' (WF:%s) → Branch: %s",
                    name, webflow_item_id, comp.name,
                )

            if cost_price and product.product_variant_id:
                product.product_variant_id.with_company(comp).sudo().write(
                    {'standard_price': cost_price}
                )

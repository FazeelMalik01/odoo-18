import requests
import logging
import json
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class WebflowCategorySync(models.Model):
    _name = 'webflow.category.sync'
    _description = 'Webflow Category Sync'


    def _get_webflow_category_credentials(self):
        ICP = self.env['ir.config_parameter'].sudo()
        token         = ICP.get_param('webflow.auth_token')
        collection_id = ICP.get_param('webflow.categories_collection_id')
        return token, collection_id
    
    def sync_categories(self):
        token, collection_id = self._get_webflow_category_credentials()

        if not token or not collection_id:
            _logger.error(
                "[ABORT] Webflow category sync: auth_token or categories_collection_id not set."
            )
            return

        url = f"https://api.webflow.com/v2/collections/{collection_id}/items"

        headers = {
            "Authorization": f"Bearer {token}",
            "accept": "application/json",
        }

        limit = 100
        offset = 0
        total = 1

        total_processed = 0
        page_number = 1

        _logger.info("[START] Webflow Category Sync Started")

        while offset < total:
            params = {
                "limit": limit,
                "offset": offset
            }

            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                _logger.error(f"[ERROR] API request failed at offset {offset}: {str(e)}")
                break

            items = data.get("items", [])
            pagination = data.get("pagination", {})
            total = pagination.get("total", 0)

            _logger.info(
                f"[PAGE {page_number}] Offset={offset}, "
                f"Fetched={len(items)}, Total={total}"
            )

            if not items:
                _logger.warning(f"[WARNING] No items returned at offset {offset}")
                break

            for item in items:
                try:
                    self._sync_single_category(item)
                    total_processed += 1
                except Exception as e:
                    _logger.error(
                        f"[ERROR] Failed processing category ID {item.get('id')}: {str(e)}"
                    )

            # ✅ Commit per page (safe for large syncs)
            self.env.cr.commit()

            offset += limit
            page_number += 1

        _logger.info(
            f"[DONE] Webflow Category Sync Completed | Total Processed: {total_processed}"
        )
    def _sync_single_category(self, item):
        fd = item.get("fieldData", {})

        category_id   = item.get("id")
        category_name = fd.get("category-full-name") or fd.get("name")

        # ── All location IDs this category belongs to ────────────────────────
        raw_locations = fd.get("locations")
        if isinstance(raw_locations, list):
            location_ids = [l for l in raw_locations if l]
        elif isinstance(raw_locations, str) and raw_locations:
            location_ids = [raw_locations]
        else:
            location_ids = []

        addons           = fd.get("addons", []) or []
        next_level_items = fd.get("0105-next-level-items", []) or []
        prods_2023       = fd.get("prods-2023", []) or []
        add_ons          = fd.get("add-ons", []) or []
        uniques          = fd.get("uniques", []) or []
        above_the_fold   = fd.get("above-the-fold")

        if not category_name:
            _logger.warning("[SKIP] Category %s has no name", category_id)
            return

        if not location_ids:
            _logger.warning(
                "[SKIP] Category '%s' (%s) has no location IDs — skipping entirely.",
                category_name, category_id
            )
            return

        Category = self.env['product.category'].sudo()
        Company  = self.env['res.company'].sudo()

        for webflow_loc_id in location_ids:

            # ── Match branch by Webflow Location ID ──────────────────────────
            company = Company.search(
                [('webflow_location_id', '=', webflow_loc_id)],
                limit=1
            )

            if not company:
                _logger.warning(
                    "[SKIP] Category '%s' — no branch found for webflow_location_id '%s'. Skipping.",
                    category_name, webflow_loc_id
                )
                continue

            # ── Upsert: match by webflow_category_id + company ───────────────
            existing = Category.search([
                ('webflow_category_id', '=', category_id),
                ('company_id', '=', company.id),
            ], limit=1)

            vals = {
                'name':                    category_name,
                'webflow_category_id':     category_id,
                'webflow_location_id':     webflow_loc_id,
                'company_id':              company.id,
                'webflow_addons':          json.dumps(addons),
                'webflow_next_level_items': json.dumps(next_level_items),
                'webflow_prods_2023':      json.dumps(prods_2023),
                'webflow_add_ons':         json.dumps(add_ons),
                'webflow_uniques':         json.dumps(uniques),
                'webflow_above_the_fold':  json.dumps(above_the_fold) if above_the_fold else False,
            }

            if existing:
                existing.write(vals)
                _logger.info(
                    "[UPDATE] '%s' (WF:%s) → Branch: %s (id=%s)",
                    category_name, category_id, company.name, company.id
                )
            else:
                Category.create(vals)
                _logger.info(
                    "[CREATE] '%s' (WF:%s) → Branch: %s (id=%s)",
                    category_name, category_id, company.name, company.id
                )
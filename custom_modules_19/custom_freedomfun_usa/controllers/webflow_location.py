import requests
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class WebflowLocationSync(models.TransientModel):
    _name = 'webflow.location.sync'
    _description = 'Webflow Location Sync'

    def _get_webflow_credentials(self):
        ICP = self.env['ir.config_parameter'].sudo()
        token         = ICP.get_param('webflow.auth_token')
        collection_id = ICP.get_param('webflow.location_collection_id')
        return token, collection_id

    def sync_locations(self):
        token, collection_id = self._get_webflow_credentials()

        if not token or not collection_id:
            _logger.error(
                "Webflow sync aborted: auth_token or location_collection_id not set."
            )
            return

        url     = f"https://api.webflow.com/v2/collections/{collection_id}/items"
        headers = {
            "Authorization": f"Bearer {token}",
            "accept":        "application/json",
        }

        all_items = []
        offset    = 0
        limit     = 100

        while True:
            _logger.info("Fetching Webflow locations — offset=%s limit=%s", offset, limit)
            try:
                resp = requests.get(
                    url,
                    headers=headers,
                    params={"limit": limit, "offset": offset},
                    timeout=30,
                )
            except Exception as e:
                _logger.exception("Webflow API request failed: %s", e)
                break

            if resp.status_code != 200:
                _logger.error("Webflow API error %s: %s", resp.status_code, resp.text)
                break

            payload = resp.json()
            items   = payload.get("items", [])
            total   = payload.get("pagination", {}).get("total", 0)

            all_items.extend(items)
            _logger.info(
                "Pagination — total=%s fetched=%s cumulative=%s",
                total, len(items), len(all_items)
            )

            if not items or len(all_items) >= total:
                break
            offset += limit

        _logger.info("Webflow returned %s location items.", len(all_items))

        with self._suppress_chart_loading():
            for item in all_items:
                try:
                    with self.env.cr.savepoint():
                        self._sync_single_location(item)
                except Exception as e:
                    _logger.exception(
                        "Failed to sync location item %s: %s", item.get("id"), e
                    )

    def _sync_single_location(self, item):
        fd = item.get("fieldData", {})

        webflow_location_id   = item.get("id") or fd.get("location-id")
        webflow_collection_id = fd.get("collection-id")
        webflow_locale_id     = fd.get("locale-id")

        company_name = fd.get("company-name") or fd.get("name")
        email        = fd.get("email")
        phone        = fd.get("phone-number")
        street       = fd.get("address")
        city_name = fd.get("city-name") or fd.get("city")
        zip_code     = fd.get("zips-supported")
        website      = fd.get("url")
        country_code = fd.get("country")
        state_name   = fd.get("state")

        if not company_name:
            _logger.warning("Skipping item %s — no company name.", webflow_location_id)
            return

        # ── Resolve country ──────────────────────────────────────────────────
        country = self.env['res.country'].sudo().search(
            [('code', '=', country_code)], limit=1
        ) if country_code else self.env['res.country'].browse()

        # ── Resolve state ────────────────────────────────────────────────────
        state = self.env['res.country.state'].sudo().search(
            [('name', 'ilike', state_name), ('country_id', '=', country.id)], limit=1
        ) if state_name and country else self.env['res.country.state'].browse()

        # ── Find existing branch ─────────────────────────────────────────────
        Branch = self.env['res.company'].sudo()

        company = Branch.search(
            [('webflow_location_id', '=', webflow_location_id), ('parent_id', '=', 1)],
            limit=1
        )
        if not company:
            company = Branch.search(
                [('name', '=', company_name), ('parent_id', '=', 1)],
                limit=1
            )

        # Fields safe to use in both create and update
        common_vals = {
            'name':                  company_name,
            'email':                 email,
            'phone':                 phone,
            'street':                street,
            'city':                  city_name,
            'zip':                   zip_code,
            'website':               website,
            'webflow_collection_id': webflow_collection_id,
            'webflow_locale_id':     webflow_locale_id,
            'webflow_location_id':   webflow_location_id,
            'webflow_zips':          zip_code,
        }
        if country:
            common_vals['country_id'] = country.id
        if state:
            common_vals['state_id'] = state.id

        if company:

            company.write(common_vals)
            _logger.info("Updated branch: %s (id=%s)", company_name, company.id)
        else:
            create_vals = dict(
                common_vals,
                parent_id=1,
                chart_template=False,   # explicit False = NULL in DB
            )
            company = Branch.create(create_vals)

            self.env.cr.execute(
                "UPDATE res_company SET chart_template = NULL WHERE id = %s",
                (company.id,)
            )

            _logger.info("Created branch: %s (id=%s)", company_name, company.id)
            self._give_admin_branch_access(company)

    # ------------------------------------------------------------------
    # Chart-of-accounts suppression — context manager
    # ------------------------------------------------------------------

    from contextlib import contextmanager

    @contextmanager
    def _suppress_chart_loading(self):

        ChartTemplate = self.env.registry['account.chart.template']
        original_try_loading = ChartTemplate.try_loading

        def _patched_try_loading(self_ct, template_code, company=None,
                                  install_demo=False, force_create=False):
            # Skip branch companies entirely — they inherit from parent.
            target = company or self_ct.env.company
            if target and target.parent_id:
                _logger.info(
                    "Skipping chart-of-accounts load for branch company %s (id=%s) — "
                    "branch companies inherit accounting from their parent.",
                    target.name, target.id,
                )
                return
            return original_try_loading(
                self_ct, template_code, company=company,
                install_demo=install_demo, force_create=force_create,
            )

        ChartTemplate.try_loading = _patched_try_loading
        _logger.info("Chart-of-accounts loader patched for Webflow location sync.")
        try:
            yield
        finally:
            ChartTemplate.try_loading = original_try_loading
            _logger.info("Chart-of-accounts loader restored.")

    # ------------------------------------------------------------------
    # Admin access helper
    # ------------------------------------------------------------------

    def _give_admin_branch_access(self, branch_company):
        if not branch_company or not branch_company.exists():
            return

        admin_group     = self.env.ref('base.group_system').sudo()
        admins          = admin_group.user_ids.filtered(lambda u: u.active)
        all_company_ids = self.env['res.company'].sudo().search([]).ids
        env             = self.env(context=dict(self.env.context, allowed_company_ids=all_company_ids))

        for admin in admins:
            if branch_company.id in admin.company_ids.ids:
                continue
            try:
                admin.with_env(env).sudo().write({
                    'company_ids': [(4, branch_company.id)]
                })
            except Exception as e:
                _logger.exception(
                    "Failed to add branch %s to admin %s: %s",
                    branch_company.id, admin.id, e
                )
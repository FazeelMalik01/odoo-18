from odoo import http, fields
from odoo.http import request
import json
import logging
import re

_logger = logging.getLogger(__name__)


class WebflowWebhookController(http.Controller):

    def _normalize_branch_name(self, name):
        if not name:
            return ""

        name = re.sub(r"\(.*?\)", "", name)
        name = re.sub(r"[^a-zA-Z0-9\s]", " ", name)
        name = name.lower()
        name = " ".join(name.split())

        return name.strip()

    def _give_admin_branch_access(self, branch_company):
        """Add the new branch (company) to company_ids for all Administrator users (role = Administrator / base.group_system)."""
        if not branch_company or not branch_company.exists():
            return

        # Users with Role = Administrator (base.group_system)
        admin_group = request.env.ref('base.group_system').sudo()
        admins = admin_group.user_ids.filtered(lambda u: u.active)

        # Run in a context that allows all companies so the write is not restricted
        all_company_ids = request.env['res.company'].sudo().search([]).ids
        env = request.env(context=dict(request.env.context, allowed_company_ids=all_company_ids))

        updated = 0
        for admin in admins:
            if branch_company.id in admin.company_ids.ids:
                continue
            try:
                admin.with_env(env).sudo().write({
                    'company_ids': [(4, branch_company.id)]
                })
                updated += 1
                _logger.info(
                    "Added branch '%s' (id=%s) to Administrator user '%s' (id=%s).",
                    branch_company.name, branch_company.id, admin.name, admin.id
                )
            except Exception as e:
                _logger.exception(
                    "Failed to add branch %s to admin user %s: %s",
                    branch_company.id, admin.id, e
                )

        if updated:
            _logger.warning(
                "Branch access: added '%s' to company_ids for %s Administrator user(s).",
                branch_company.name, updated
            )

    @http.route('/webflow/webhook/lead', type='http', auth='public', methods=['POST'], csrf=False)
    def webflow_lead(self, **kwargs):

        try:

            raw_data = request.httprequest.data

            _logger.warning("====== WEBFLOW WEBHOOK HIT ======")
            _logger.warning("Raw Payload: %s", raw_data)

            data = json.loads(raw_data.decode('utf-8'))
            form_data = data.get("data") or data.get("payload", {}).get("data", {})

            name = form_data.get("Name")
            email = form_data.get("E-Mail")
            phone = form_data.get("Phone")
            zip_code = form_data.get("Zip")
            event_type = form_data.get("Event Type")
            notes = form_data.get("Party Notes")
            contact_type = form_data.get("Contact Type")
            page_url = form_data.get("Page URL")

            # --------------------------------------------------
            # PARTNER LOGIC
            # --------------------------------------------------

            partner = None

            if email:
                partner = request.env['res.partner'].sudo().search(
                    [('email', '=', email)],
                    limit=1
                )

            if not partner and name:
                partner = request.env['res.partner'].sudo().create({
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'zip': zip_code,
                })

            # --------------------------------------------------
            # COMPANY / BRANCH LOGIC
            # --------------------------------------------------

            main_company = request.env['res.company'].sudo().browse(1)
            branch_company = None

            if page_url and "/location/" in page_url:

                slug = page_url.split("/location/")[-1].strip("/")
                location_path = f"/location/{slug}"

                _logger.warning("Location Slug Detected: %s", slug)

                companies = request.env['res.company'].sudo().search([
                    ('parent_id', '=', 1)
                ])

                matched_company = None

                # ----------------------------------------------
                # 1️⃣ Match by website slug
                # ----------------------------------------------
                for company in companies:
                    if company.website and location_path in company.website:
                        matched_company = company
                        _logger.warning(
                            "Matched Branch By Website Slug: %s",
                            company.name
                        )
                        break

                # ----------------------------------------------
                # 2️⃣ Match by branch name if website failed
                # ----------------------------------------------
                if not matched_company:

                    branch_name = slug.replace("-", " ").title()
                    normalized_slug = self._normalize_branch_name(branch_name)

                    for company in companies:
                        normalized_existing = self._normalize_branch_name(company.name)

                        if normalized_existing == normalized_slug:
                            matched_company = company
                            _logger.warning(
                                "Matched Branch By Name: %s",
                                company.name
                            )
                            break

                # ----------------------------------------------
                # 3️⃣ If branch found
                # ----------------------------------------------
                if matched_company:
                    branch_company = matched_company

                # ----------------------------------------------
                # 4️⃣ If branch not found → create
                # ----------------------------------------------
                else:

                    branch_name = slug.replace("-", " ").title()

                    branch_company = request.env['res.company'].sudo().create({
                        'name': branch_name,
                        'parent_id': 1,
                        'website': page_url,
                    })

                    _logger.warning(
                        "Created New Branch: %s | URL: %s",
                        branch_company.name, page_url
                    )

                    self._give_admin_branch_access(branch_company)

            # --------------------------------------------------
            # NO LOCATION → MAIN COMPANY
            # --------------------------------------------------

            else:
                branch_company = main_company

            # Safety fallback
            if not branch_company:
                branch_company = main_company

            # --------------------------------------------------
            # CRM STAGE
            # --------------------------------------------------

            stage = request.env['crm.stage'].sudo().search([], limit=1)

            description = f"""
Event Type: {event_type}
Party Notes: {notes}
Preferred Contact: {contact_type}
Page URL: {page_url}
Submitted At: {data.get('submittedAt') or data.get('d')}
"""

            lead_vals = {
                "name": f"{event_type or 'New Inquiry'} - {name or ''}",
                "partner_id": partner.id if partner else False,
                "contact_name": name,
                "email_from": email,
                "phone": phone,
                "zip": zip_code,
                "event_type": event_type,
                "party_notes": notes,
                "page_url": page_url,
                "contact_type": contact_type,
                "company_id": branch_company.id,
                "description": description,
                "type": "opportunity",
                "stage_id": stage.id if stage else False,
                "submitted_at": data.get("submittedAt") or fields.Datetime.to_string(fields.Datetime.now()),
            }

            _logger.warning("Lead Values:\n%s", json.dumps(lead_vals, indent=4))

            lead = request.env['crm.lead'].sudo().create(lead_vals)

            _logger.warning("Lead Created Successfully ID: %s", lead.id)

            return request.make_response(
                json.dumps({
                    "status": "success",
                    "lead_id": lead.id
                }),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:

            _logger.error("Webhook Error: %s", str(e))

            return request.make_response(
                json.dumps({
                    "status": "error",
                    "message": str(e)
                }),
                headers=[('Content-Type', 'application/json')]
            )
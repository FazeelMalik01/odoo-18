from odoo import http, fields
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class WebflowWebhookController(http.Controller):

    @http.route('/webflow/webhook/lead', type='http', auth='public', methods=['POST'], csrf=False)
    def webflow_lead(self, **kwargs):

        try:
            raw_data = request.httprequest.data

            _logger.warning("====== WEBFLOW WEBHOOK HIT ======")
            _logger.warning("Raw Payload: %s", raw_data)

            data = json.loads(raw_data.decode('utf-8'))
            form_data = data.get("data") or data.get("payload", {}).get("data", {})

            name          = form_data.get("Name")
            email         = form_data.get("E-Mail")
            phone         = form_data.get("Phone")
            zip_code      = form_data.get("Zip")
            event_type    = form_data.get("Event Type")
            notes         = form_data.get("Party Notes")
            contact_type  = form_data.get("Contact Type")
            page_url      = form_data.get("Page URL")
            collection_id = form_data.get("Collection-ID")
            locale_id     = form_data.get("Locale-ID")
            catalog_id    = form_data.get("Catalog-ID")
            location_id   = form_data.get("Location-ID")

            # ── Resolve company from location_id ──────────────────────────────
            company = None
            if location_id:
                company = request.env['res.company'].sudo().search(
                    [('webflow_location_id', '=', location_id)],
                    limit=1
                )
                if company:
                    _logger.warning("Location-ID '%s' matched company: ID=%s | Name=%s", location_id, company.id, company.name)
                else:
                    _logger.warning("Location-ID '%s' did not match any company. Using main company.", location_id)

            if not company:
                company = request.env['res.company'].sudo().search([('parent_id', '=', False)], limit=1)
                _logger.warning("Using main company: ID=%s | Name=%s", company.id, company.name)
            # ─────────────────────────────────────────────────────────────────

            salesperson = request.env['res.users']
            crm_sales_group = request.env.ref(
                'custom_freedomfun_usa.group_crm_sales_person',
                raise_if_not_found=False
            )
            if crm_sales_group and company:
                salesperson = request.env['res.users'].sudo().search([
                    ('active', '=', True),
                    ('share', '=', False),
                    ('company_id', '=', company.id),
                    ('group_ids', 'in', [crm_sales_group.id]),
                ], limit=1)

            if salesperson:
                _logger.warning(
                    "Assigned salesperson %s (id=%s) for company %s",
                    salesperson.name, salesperson.id, company.name
                )
            else:
                _logger.warning(
                    "No CRM Sale Person found for company %s. Lead will be created without salesperson.",
                    company.name if company else "N/A"
                )

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

            stage = request.env['crm.stage'].sudo().search([], limit=1)

            description = f"""
Event Type: {event_type}
Party Notes: {notes}
Preferred Contact: {contact_type}
Page URL: {page_url}
Submitted At: {data.get('submittedAt') or data.get('d')}
"""

            lead_vals = {
                "name":          f"{event_type or 'New Inquiry'} - {name or ''}",
                "partner_id":    partner.id if partner else False,
                "contact_name":  name,
                "email_from":    email,
                "phone":         phone,
                "zip":           zip_code,
                "event_type":    event_type,
                "party_notes":   notes,
                "page_url":      page_url,
                "contact_type":  contact_type,
                "description":   description,
                "type":          "opportunity",
                "stage_id":      stage.id if stage else False,
                "collection_id": collection_id,
                "locale_id":     locale_id,
                "catalog_id":    catalog_id,
                "location_id":   location_id,
                "submitted_at":  data.get("submittedAt") or fields.Datetime.to_string(fields.Datetime.now()),
                "company_id":    company.id,  # ← only addition
                "user_id":       salesperson.id if salesperson else False,
            }

            _logger.warning("Lead Values:\n%s", json.dumps(lead_vals, indent=4))

            lead = request.env['crm.lead'].sudo().create(lead_vals)

            _logger.warning("Lead Created Successfully ID: %s", lead.id)

            return request.make_response(
                json.dumps({"status": "success", "lead_id": lead.id}),
                headers=[('Content-Type', 'application/json')]
            )

        except Exception as e:
            _logger.error("Webhook Error: %s", str(e), exc_info=True)

            return request.make_response(
                json.dumps({"status": "error", "message": str(e)}),
                headers=[('Content-Type', 'application/json')]
            )
from odoo import fields, models, api
import json
import base64
import requests
class ProductCategory(models.Model):
    _inherit = 'product.category'

    webflow_category_id = fields.Char("Webflow Category ID", index=True)
    webflow_location_id = fields.Char("Webflow Location ID", index=True)
    company_id = fields.Many2one('res.company', string="Company")

    webflow_addons = fields.Text("Addons JSON")
    webflow_next_level_items = fields.Text("Next Level Items JSON")
    webflow_prods_2023 = fields.Text("Products 2023 JSON")
    webflow_add_ons = fields.Text("Add-ons JSON")
    webflow_uniques = fields.Text("Uniques JSON")
    webflow_above_the_fold = fields.Text("Above The Fold JSON")

    webflow_above_the_fold_image_url = fields.Char(
        compute='_compute_above_the_fold_image_url',
        store=False,
    )
    webflow_above_the_fold_image = fields.Image(
        compute='_compute_above_the_fold_image',
        store=False,
    )

    @api.depends('webflow_above_the_fold')
    def _compute_above_the_fold_image_url(self):
        for rec in self:
            try:
                data = json.loads(rec.webflow_above_the_fold or '{}')
                rec.webflow_above_the_fold_image_url = data.get('url') or False
            except Exception:
                rec.webflow_above_the_fold_image_url = False

    @api.depends('webflow_above_the_fold_image_url')
    def _compute_above_the_fold_image(self):
        for rec in self:
            try:
                url = rec.webflow_above_the_fold_image_url
                if url:
                    resp = requests.get(url, timeout=10)
                    resp.raise_for_status()
                    rec.webflow_above_the_fold_image = base64.b64encode(resp.content)
                else:
                    rec.webflow_above_the_fold_image = False
            except Exception:
                rec.webflow_above_the_fold_image = False
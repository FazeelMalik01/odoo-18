from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    webflow_product_collection_id = fields.Char(
        string="Product Collection ID",
        config_parameter='webflow.product_collection_id',
    )
    webflow_location_collection_id = fields.Char(
        string="Location Collection ID",
        config_parameter='webflow.location_collection_id',
    )
    webflow_categories_collection_id = fields.Char(
        string="Categories Collection ID",
        config_parameter='webflow.categories_collection_id',
    )
    webflow_addons_collection_id = fields.Char(
        string="Addons Collection ID",
        config_parameter='webflow.addons_collection_id',
    )
    webflow_next_collection_id = fields.Char(
        string="Next Collection ID",
        config_parameter='webflow.next_collection_id',
    )
    webflow_unique_collection_id = fields.Char(
        string="Unique Collection ID",
        config_parameter='webflow.unique_collection_id',
    )
    webflow_auth_token = fields.Char(
        string="Auth Token",
        config_parameter='webflow.auth_token',
    )

    def action_sync_webflow_locations(self):
        self.env['webflow.location.sync'].sync_locations()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Webflow Sync',
                'message': 'Locations synced successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_sync_webflow_categories(self):
        self.env['webflow.category.sync'].sync_categories()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Webflow Sync',
                'message': 'Categories synced successfully!',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_sync_webflow_products(self):
        self.env['webflow.product.sync'].sync_products()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Webflow Product Sync',
                'message': 'Products synced successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_sync_webflow_addons(self):
        self.env['webflow.addons.sync'].sync_addons()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Webflow Addons Sync',
                'message': 'Addons synced successfully!',
                'type': 'success',
                'sticky': False,
            }
        }
# -*- coding: utf-8 -*-
import logging
from lxml import html
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

logger = logging.getLogger(__name__)


class WebsiteShopProductLazy(WebsiteSale):

    @http.route([
        '/shop-lazy',
        '/shop-lazy/page/<int:page>',
        '/shop-lazy/category/<model("product.public.category"):category>',
        '/shop-lazy/category/<model("product.public.category"):category>/page/<int:page>',
        '/<string:lang>/shop-lazy',
        '/<string:lang>/shop-lazy/page/<int:page>',
        '/<string:lang>/shop-lazy/category/<model("product.public.category"):category>',
        '/<string:lang>/shop-lazy/category/<model("product.public.category"):category>/page/<int:page>',
    ], type='json', auth="public", website=True, csrf=False)
    def lazyload(self, lang=None, page=1, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        logger.info(f"=== LAZY LOAD START ===")
        logger.info(f"Params - lang: {lang}, page: {page}, category: {category}, search: {search}")

        try:
            # Set language if provided
            if lang:
                # Check if language exists
                lang_exists = request.env['res.lang']._lang_get(lang)
                if lang_exists:
                    request.context = dict(request.context, lang=lang)
                    logger.info(f"Language set to: {lang}")
                else:
                    logger.warning(f"Language {lang} not found, using default")

            # Convert page to 0-based for Odoo internal use
            odoo_page = max(0, page - 1)
            logger.info(f"Using Odoo page: {odoo_page} (converted from user page: {page})")

            # Set default ppg
            if not ppg:
                ppg = 20

            # Prepare shop parameters
            shop_params = {
                'page': odoo_page,
                'ppg': ppg,
                'search': search,
                'min_price': min_price,
                'max_price': max_price,
            }

            if category:
                shop_params['category'] = category

            logger.info(f"Calling shop() with params: {shop_params}")

            # Call the original shop method
            result_super = super(WebsiteShopProductLazy, self).shop(**shop_params, **post)

            logger.info(f"Shop method executed successfully")
            logger.info(f"Result type: {type(result_super)}")

            # Render the template to HTML
            rendered_html = result_super.render()
            html_string = str(rendered_html)

            logger.info(f"Rendered HTML length: {len(html_string)}")

            # Parse HTML
            html_tree = html.fromstring(html_string)

            # Debug: Save HTML for inspection
            # with open('/tmp/debug_arabic_shop.html', 'w') as f:
            #     f.write(html_string)

            # Find products container - try multiple selectors
            container_selectors = [
                '//div[@class="o_wsale_products_grid_table_wrapper pt-3 pt-lg-0"]',
                '//div[contains(@class, "o_wsale_products_grid_table_wrapper")]',
                '//div[@id="products_grid"]',
                '//section[contains(@class, "products")]',
                '//div[contains(@class, "products")]',
            ]

            htmlProductTbody = None
            for selector in container_selectors:
                elements = html_tree.xpath(selector)
                if elements:
                    htmlProductTbody = elements[0]
                    logger.info(f"Found container using selector: {selector}")
                    break

            if not htmlProductTbody:
                logger.error("No products container found with any selector")
                return {
                    'success': False,
                    'error': 'No products container found',
                    'count': 0,
                    'tableWrapper': '',
                    'debug': {
                        'html_sample': html_string[:500] if html_string else 'No HTML',
                        'selectors_tried': container_selectors
                    }
                }

            # Find products - try multiple selectors
            product_selectors = [
                '//div[@data-name="Product"]',
                '//div[contains(@class, "oe_product_cart")]',
                '//div[contains(@class, "product")]',
                '//div[contains(@class, "o_wsale_product")]',
            ]

            productCount = []
            for selector in product_selectors:
                products = html_tree.xpath(selector)
                if products:
                    productCount = products
                    logger.info(f"Found {len(products)} products using selector: {selector}")
                    break

            # Get the container HTML
            container_html = html.tostring(htmlProductTbody, encoding='unicode', pretty_print=True)

            logger.info(f"=== LAZY LOAD SUCCESS ===")
            logger.info(f"Returning {len(productCount)} products for lang: {lang}, page: {page}")

            return {
                'success': True,
                'tableWrapper': container_html,
                'count': len(productCount),
                'debug': {
                    'lang': lang,
                    'page': page,
                    'products_found': len(productCount),
                    'container_selector_used': selector if htmlProductTbody else None
                }
            }

        except Exception as e:
            logger.error(f"=== LAZY LOAD ERROR ===")
            logger.error(f"Error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'count': 0,
                'tableWrapper': '',
                'debug': {
                    'lang': lang,
                    'page': page,
                    'exception_type': type(e).__name__
                }
            }
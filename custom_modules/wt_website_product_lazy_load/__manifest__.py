{
    'name': "Website Product Lazy Load",
    'summary': "Seamless scrolling and optimized loading speed for eCommerce.",
    'description': """Enhance your customers' shopping experience with lazy loading...""",
    'author': "Wisenetic",
    'website': "https://www.wisenetic.com",
    "support": "info@wisenetic.com",
    'category': 'website',
    'version': '18.0.0.0.1',
    'depends': ['website_sale'],
    'data': [
        'views/website_sale_templates.xml',
        'views/snippets.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'wt_website_product_lazy_load/static/src/js/lazy_load.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'OPL-1',
    'price': '24.99',
    'currency': 'USD'
}
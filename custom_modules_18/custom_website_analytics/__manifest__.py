# -*- coding: utf-8 -*-
{
    'name': "custom_website_analytics",
    'summary': "Link an analytic account to a website and apply it to sale order lines",
    'description': """
        Adds an analytic account field to the Website Settings form.
        When a sale order is placed via that website, the analytic account
        is automatically set on every sale order line.
    """,
    'author': "My Company",
    'website': "https://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': [
        'website',
        'sale',
        'analytic',
    ],
    'data': [
        'views/views.xml',
    ],
}
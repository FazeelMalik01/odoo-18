# -*- coding: utf-8 -*-
{
    'name': "Payment Provider: Flooss",
    'summary': "Payment Provider for online payments",
    'description': " ",
    'author': "Muhammad Faizan",
    'website': "https://www.developerspro.co.uk",
    'category': 'Accounting/Payment Providers',
    'version': '0.1',
    'depends': ['payment','website'],

    'data': [
        'views/payment_form_templates.xml',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',
        'views/payment_flooss_modal.xml',
        'views/success_flooss.xml'

],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
            'payment_flooss/static/src/js/payment_button.js',
            'payment_flooss/static/src/js/payment_form.js',
        ],
    },
      'license': 'LGPL-3',
  
}


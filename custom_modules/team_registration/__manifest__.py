# -*- coding: utf-8 -*-
{
    'name': "Team Registration",

    'summary': "This is A Registration Form For Peptidat Company",

    'description': """
Long description of module's purpose
    """,

    'author': "Majid Mohammed",
    'email': "majidmohammed1096@gmail.com",
    'phone': "+962787510196",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    "version": "15.9.25",

    # any module necessary for this one to work correctly
    'depends': ['base', 'web','website', 'sale', 'sale_management', 'mail', 'portal', 'payment','website_sale_dashboard','account','loyalty'],

    # always loaded
    'data': [
        'groups/groups.xml',
        'security/ir.model.access.csv',
        'data/commission_cron.xml',
        'views/registration_template.xml',
        'views/thank_you_template.xml',
        'views/res_users.xml',
        'views/res_company.xml',
        'views/user_already_exists.xml',
        'views/team_registration_views.xml',
        'views/commission_slices_views.xml',
        'views/coach_commission_period.xml',
        'views/team_registration_menu.xml',
        'views/website_home_page.xml',
        'views/portal_my_team_template.xml',
        'views/portal_side_content.xml',
        'views/website_address_template.xml',
        'views/dashboard.xml',
        'views/card.xml',
        'views/commission_details_card.xml',
        'views/portal_commission_details_template.xml',
    
            
      
       
    ],
    "assets": {
    "web.assets_frontend": [
        "team_registration/static/src/js/commission_topup.js",
        
    ],
},

    'application': True,
}

{
    "name": "Custom POS",
    "version": "0.1",
    "summary": "POS Customisaion",
    "description": "Small module to increase POS receipt font size for printers and browser preview.",
    "category": "Point of Sale",
    "author": "Waqas Riasat",
    "company": "Waqas Riasat",
    "maintainer": "Waqas Riasat",
    "website": "",
    "license": "AGPL-3",
    "depends": ["pos_hr_restaurant"],
    "data": [
        'views/pos_daily_sale_report.xml',
        'views/res_config_settings.xml'
    ],
    'assets': {
            'point_of_sale._assets_pos': [
                'custom_pos/static/src/**/*',
                # 'custom_pos/static/src/overrides/*',

                # "custom_pos/static/src/js/print_reciept_qztray.js",

                "custom_pos/static/src/css/pos_note.css",
                "custom_pos/static/src/css/rtl_ltr.css",
                "custom_pos/static/src/js/order_widget_for_gen_note.js",
                "custom_pos/static/src/js/number_buffer_patch.js",
                "custom_pos/static/src/js/number_popup_patch.js",
                "custom_pos/static/src/js/customer_note.js",
                "custom_pos/static/src/js/order_custom_note_patch.js",
                # "custom_pos/static/src/js/orderline_note_button_patch.js",
                "custom_pos/static/src/js/control_buttons_patch.js",
                "custom_pos/static/src/js/patch_product_card_product_info.js",
                "custom_pos/static/src/js/pos_store.js",
                
                # ✅ RTL/LTR Support for Mixed Arabic/English Variants
                "custom_pos/static/src/js/rtl_utils.js",
                "custom_pos/static/src/js/orderline_rtl_patch.js",
                "custom_pos/static/src/js/product_configurator_rtl_patch.js",
                "custom_pos/static/src/js/orderline_order_patch.js",
                
                # ✅ Attribute Selection Order - Display in order user selected
                "custom_pos/static/src/js/attribute_selection_order_patch.js",

                # ✅ XML for button + receipt rendering
                "custom_pos/static/src/xml/pos_receipt_employee_pricelist_inherit.xml",
                "custom_pos/static/src/xml/customer_navbar_template.xml",
                "custom_pos/static/src/xml/customer_note_template.xml",
                "custom_pos/static/src/xml/customer_note.xml",
                
                # ✅ XML for RTL/LTR Product Configurator
                "custom_pos/static/src/overrides/components/product_configurator_popup.xml",
            ],
        'point_of_sale.customer_display_assets': [
            # "custom_pos/static/src/xml/customer_note.xml",
        ],
        'point_of_sale.assets_qweb': [
                # 'way4tech/custom_pos/views/res_config_settings.xml',
            ]
        },
    "installable": True,
    "application": False,
    "auto_install": False,
}
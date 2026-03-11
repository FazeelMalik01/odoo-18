# -*- coding: utf-8 -*-
#################################################################################
# Author      : CodersFort Info Solutions (<https://www.codersfort.com/>)
# Copyright(c): 2017-Present CodersFort Info Solutions.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://www.codersfort.com/>
#################################################################################

{
    "name": "Vehicle Repair | Advance Vehicle Repair | Vehicle Inspection | Fleet Repair | Car Repair | Automobile Services",
    "summary": """
        This module introduces comprehensive vehicle repair management features to Odoo, tailored to meet the needs of automotive service centers, 
        fleet managers, and vehicle owners. It integrates seamlessly into Odoo, providing a robust solution for managing vehicle inspections, 
        repairs, bookings, and related services.
    """,
    'sequence': '10',
    "version": "19.1",
    "description": """
        This module introduces comprehensive vehicle repair management features to Odoo, tailored to meet the needs of automotive service centers, 
        fleet managers, and vehicle owners. It integrates seamlessly into Odoo, providing a robust solution for managing vehicle inspections, 
        repairs, bookings, and related services.
        
        Dashboard
        Vehicle Master
        Booking
        Job Card (Inspection and Repair)
        Customers
        Teams
        Tasks
        Spare Parts
        Spare Parts Assessments
        Services
        Brands
        Models
        Fuel Types
        Locations
        Conditions
        Vehicle Items
        Components
        Fluids
        Checklist Templates
        Bookigng Appointment Slots
    """,
    "author": "CodersFort Info Solutions",
    "maintainer": "CodersFort Info Solutions",
    "license": "Other proprietary",
    "website": "https://www.codersfort.com",
    "images": ["images/advance_vehicle_repair.png"],
    "category": "Extra Tools",
    "depends": [
        'base',
        'mail',
        'product',
        'hr',
        'sale_management',
        'sales_team',
        'website',
        'portal',
        'fleet',
        'stock',
        'base_address_extended',
    ],
    "data": [
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/ir_sequence_data.xml',
        'data/vehicle_product_data.xml',
        'data/vehicle_brand_data.xml',
        'data/vehicle_model_data.xml',
        'data/vehicle_fuel_type_data.xml',
        'data/vehicle_location_data.xml',
        'data/vehicle_condition_data.xml',
        'data/vehicle_items_data.xml',
        'data/vehicle_repair_data.xml',
        'data/vehicle.appointment_data.xml',
        'data/vehicle_components_data.xml',
        'data/vehicle_fuids_data.xml',
        'data/vehicle_checklist_data.xml',
        'data/vehicle_teams_data.xml',
        'data/website_menu.xml',

        'wizard/jobcard_type_wizard.xml',
        'wizard/jobcard_inspector_wizard.xml',
        'wizard/wizard_action.xml',
        'wizard/vehicle_task_assigner_wizard.xml',

        'views/vehicle_config_menus.xml',
        'views/vehicle_brand_views.xml',
        'views/vehicle_config_model_views.xml',
        'views/vehicle_config_fuel_views.xml',
        'views/vehicle_config_location_views.xml',
        'views/vehicle_config_condition_views.xml',
        'views/vehicle_config_items_views.xml',
        'views/vehicle_item_category.xml',
        'views/vehicle_config_components_views.xml',
        'views/vehicle_config_fluids_views.xml',
        'views/vehicle_config_checklist_views.xml',
        'views/vehicle_appointment_views.xml',
        'views/vehicle_booking_views.xml',
        'views/vehicle_booking_request_views.xml',
        'views/vehicle_spare_parts_views.xml',
        'views/vehicle_spare_assessments_views.xml',
        'views/vehicle_services.xml',
        'views/vehicle_teams_views.xml',
        'views/vehicle_jobcards_repair_task.xml',
        'views/vehicle_sale_order.xml',
        'views/vehicle_customers_views.xml',
        'views/portal_booking_template.xml',
        'views/vehicle_register_views.xml',
        'views/vehicle_jobcard_views.xml',
        'views/web_template_views.xml',
        'views/vehicle_service_bundle.xml',

        'reports/vehicle_report.xml',
        'reports/vehicle_inspection_template.xml',
        'reports/vehicle_repair_template.xml',
        'reports/vehicle_scratch_template.xml',

    ],
    "assets": {
        'web.assets_backend': [
            '/advance_vehicle_repair/static/src/scss/*.scss',
            '/advance_vehicle_repair/static/src/css/*.css',
            '/advance_vehicle_repair/static/src/js/dashboard.js',
            '/advance_vehicle_repair/static/src/xml/*.xml',
        ],
        "web.assets_frontend": [
            '/advance_vehicle_repair/static/src/js/vehicle_booking_request.js',
            '/advance_vehicle_repair/static/src/js/create_vehicle_booking.js',
            '/advance_vehicle_repair/static/src/js/create_vehicle_register.js',
        ]
    },
    "installable": True,
    "application": True,
    "price": 78,
    "currency": "EUR",
}

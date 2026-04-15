# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
{
    'name': "Advanced Gym Management | Diet & Nutrion Management | Yoga Management | Fitness Management",
    'summary': """Gym Memberships, Membership Plans, Trainers, Workouts, Exercises, Diet Plans, Fitness Report 
    (BMI | BMR | BFP), & Diet Plan Report.""",
    'description': """
        - Gym management
        - Gym Members
        - Gym Memberships
        - Gym Membership Types
        - Gym Trainer
        - Gym Exercises
        - Gym Workouts
        - Yoga Classes
        - Diet Management
        - Nutrient Management
        - Diet Members
        - Diet & Nutrients Plans
        - Fitness Reports
        - BMI Report
        - BMR Report
        - BFP Report
    """,
    'category': 'Industry',
    'version': '2.3',
    'author': 'TechKhedut Inc.',
    'company': 'TechKhedut Inc.',
    'maintainer': 'TechKhedut Inc.',
    'website': "https://www.techkhedut.com",
    'depends': [
        'base',
        'mail',
        'contacts',
        'product',
        'hr',
        'sale_management',
        'hr_attendance',
        'crm',
        'website',
    ],
    'data': [
        # Security
        'security/groups.xml',
        'security/ir.model.access.csv',
        # Wizard
        'wizard/membership_renew_wizard_view.xml',
        'wizard/membership_report_xls_wizard_view.xml',
        'wizard/attendance_report_xls_wizard_view.xml',
        'wizard/create_diet_plan_wizard_views.xml',
        'wizard/diet_plan_xls_report_views.xml',
        'wizard/freeze_membership.xml',
        # Data
        'data/data.xml',
        'data/sequence.xml',
        'data/gym_days.xml',
        'data/gym_exercise_data.xml',
        'data/ir_cron.xml',
        # Views
        'views/assets.xml',
        'views/gym_membership_views.xml',
        'views/gym_membership_member_views.xml',
        'views/gym_membership_duration_views.xml',
        'views/gym_membership_category_views.xml',
        'views/gym_employee_views.xml',
        'views/gym_equipment_views.xml',
        'views/gym_exercise_for_views.xml',
        'views/gym_exercise_views.xml',
        'views/gym_member_views.xml',
        'views/gym_class_views.xml',
        'views/gym_class_type_views.xml',
        'views/gym_employee_attendance_views.xml',
        'views/gym_member_attendance_views.xml',
        'views/gym_workout_views.xml',
        'views/gym_fitness_report_views.xml',
        'views/gym_food_item_views.xml',
        'views/nutrient_type_views.xml',
        'views/diet_nutrient_views.xml',
        'views/diet_plan_views.xml',
        'views/meal_type_views.xml',
        'views/diet_meal_views.xml',
        'views/diet_meal_template_views.xml',
        'views/workout_days_views.xml',
        'views/gym_tag_views.xml',
        'views/invoice_inherit_views.xml',
        'views/res_config_settings_view.xml',
        'views/diet_plan_template_views.xml',
        'views/diet_category_views.xml',
        'views/diet_type_views.xml',
        'views/crm_lead_inherit_view.xml',
        # Mail Template
        'data/membership_expiring_reminder_mail_template.xml',
        # Menus
        'views/menus.xml',
        # Templates
        'views/templates/diet_request_form.xml',
        # Reports
        'report/diet_reports.xml',
        'report/fitness_reports.xml',
        'report/workout_reports.xml',
        'report/exercise_reports.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tk_gym_management/static/src/xml/template.xml',
            'tk_gym_management/static/src/xml/diet_template.xml',
            'tk_gym_management/static/src/scss/style.scss',
            'tk_gym_management/static/src/js/lib/apexcharts.js',
            'tk_gym_management/static/src/js/lib/index.js',
            'tk_gym_management/static/src/js/lib/Animated.js',
            'tk_gym_management/static/src/js/lib/percent.js',
            'tk_gym_management/static/src/js/lib/xy.js',
            'tk_gym_management/static/src/js/lib/Responsive.js',
            'tk_gym_management/static/src/js/gym.js',
            'tk_gym_management/static/src/js/diet.js',
        ],
    },
    'images': ['static/description/gym-management.gif'],
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 99,
    'currency': 'USD',
}

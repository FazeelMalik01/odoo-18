{
    "name": "Custom Approvals",
    "summary": "Manage multi-level approval workflows for business processes",
    "description": """
Custom Approvals Module
=======================

This module provides a flexible approval system that allows businesses to define 
and manage multi-level approval workflows for different operations such as 
purchase requests, expenses, or custom records.

Key Features:
-------------
- Multi-level approval hierarchy
- Role-based approval access
- Approval status tracking (draft, pending, approved, rejected)
- Email/activity notifications for approvers
- Integration-ready with other modules (e.g., Purchase, HR)

Use Cases:
----------
- Purchase requisition approvals
- Expense approvals
- Custom workflow approvals
    """,
    "author": "My Company",
    "website": "https://www.yourcompany.com",
    "category": "Productivity",
    "version": "1.0.0",
    "license": "LGPL-3",
    # Required dependencies
    "depends": ["base", "mail", "sale", "purchase", "project", "hr_timesheet", "project_forecast", "hr_holidays"],
    "data": [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/mail_template_timesheet_approval.xml',
        'views/expense_menu_config.xml',
        'views/sale_order_views.xml',
        'views/sale_settings.xml',
        'views/purchase_settings.xml',
        'views/purchase_order.xml',
        'views/sale_order_discount_views.xml',
        'views/expense_settings.xml',
        'views/expense_form.xml',
        'views/timesheet_settings.xml',
        'views/timesheet_approval_views.xml',
        'views/portal_task_timer_template.xml',
        'views/planning_slot_task_views.xml',
        'views/time_off_settings.xml',
        'views/time_off_form.xml',
        'views/invoice_setting.xml',
        'views/invoice_form.xml',
        'views/invoice_approval_menu.xml'
    ],

    "installable": True,
    "application": True,
    "auto_install": False,
}

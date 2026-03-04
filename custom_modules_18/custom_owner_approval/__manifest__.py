# -*- coding: utf-8 -*-
{
    "name": "Owner Approvals",
    "summary": "Contractor-side owner approval legal register",
    "description": """
Owner Approval Register (Internal)

This module provides a legal-grade logbook for tracking all
owner / consultant approvals submitted by the contractor.

Core objectives:
- Traceable reference numbers
- Project and contract context
- Submission and response deadlines
- Overdue evidence for claims
- Decision history with documents

This is a forensic data layer, not a workflow system.
    """,
    "author": "Tech Cogg",
    "website": "https://www.techcogg.com",
    "category": "Project",
    "version": "18.0.1.0.0",
    "depends": [
        "account",
        "base",
        "portal",
        "project",
        "mail",
        "web",
    ],
    "data": [
        "security/owner_approval_group.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/cron.xml",
        "views/owner_approval_list.xml",
        "views/owner_approval_form.xml",
        "views/owner_approval_action.xml",
        "views/owner_approval_menu.xml",
        "views/owner_approval_card.xml",
        "views/owner_approval_portal_list.xml",
        "views/owner_approval_breadcrumb.xml",
        "views/owner_approval_detail.xml",
        "views/owner_portal_information.xml",
        "views/owner_approval_portal_invoice.xml",
        "report/owner_approval_report.xml"
    ],
    'assets': {
        'web.assets_frontend': [
            'custom_owner_approval/static/src/js/filter.js',
            'custom_owner_approval/static/src/js/pagination.js',
        ],
    },
    "demo": [],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}

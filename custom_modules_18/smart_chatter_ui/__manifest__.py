{
    "name": "Enhanced Chatter UI (Draggable, Resizable & Toggle)",
    "summary": "Hide and Show chatter smartly in any form view, Make Odoo Chatter draggable, resizable, collapsible, and toggle-friendly with floating Show button.",
    
    'description': """
Smart Chatter UI
================
This module allows you to hide and show the chatter panel easily across all form views (Sales, CRM, Invoices, etc.).""",

    "version": "18.0",
    "category": "Discuss/Chatter",
    "author": "Apurva Wanjari",
    "license": "LGPL-3",
    "depends": ["mail", "web", "sale_management"],
    "assets": {
        "web.assets_backend": [
            "smart_chatter_ui/static/src/js/chatter_resize.js",
            "smart_chatter_ui/static/src/css/chatter_resize.css",
        ],
    },
    
    "images": ["static/description/banner.png"],
    "application": False,
    "installable": True,
    "auto_install": False,
}

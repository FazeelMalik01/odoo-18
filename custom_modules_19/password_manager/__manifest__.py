{
    "name": "Password Manager",
    "version": "1.0",
    "summary": "Secure password storage with encryption and audit trail",
    "category": "Tools",
    "author": "Interview Test",
    "depends": ["base", "mail", "web"],
    "external_dependencies": {
        "python": ["cryptography"],
    },
    "data": [
        "security/ir.model.access.csv",
        "security/password_entry_rules.xml",
        "views/password_entry_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "password_manager/static/src/js/password_view_copy_widget.js",
        ],
    },
    "installable": True,
    "application": True,
}

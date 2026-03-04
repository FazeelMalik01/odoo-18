# -*- coding: utf-8 -*-
# Part of Odoo, Aktiv Software.
# See LICENSE file for full copyright & licensing details.

# Author: Aktiv Software.
# mail: odoo@aktivsoftware.com
# Copyright (C) 2015-Present Aktiv Software PVT. LTD.
# Contributions:
# Aktiv Software:
# - Kuldip Trapasiya
# - Tanvi Gajera

{
    "name": "Signup using OTP via Twilio SMS",
    "summary": """ Signup using OTP Verification with the help of Twilio SMS Gateway
    twilio,
    signup,
    signin,
    reset,
    reset password,
    password reset,
    sms,
    otp,
    otp verify,
    verify otp,
    otp verification,
    signup otp verification,
    reset otp verification,
    reset password otp verification,
    mobile otp,
    phone otp,
    otp mobile,
    otp phone,
    signup,
    signin,
    reset,
    reset password,
    signup mobile,
    signup with mobile,
    signup with phone,
    signup with number,
    phone signup,
    mobile signup,
    signin mobile,
    signin with number,
    signin with mobile,
    signin with phone,
    phone signin,
    mobile signin,
    signin number,
    signup number,
    signin with number,
    signup with number,
    number signin,
    number signup
    """,
    "description": """
    Title: Signup With Mobile Number \n
    Author: Aktiv Software PVT. LTD. \n
    mail: odoo@aktivsoftware.com \n
    Copyright (C) 2015-Present Aktiv Software PVt. LTD. \n
    Contributions: Aktiv Software \n
        Contributions: Aktiv Software:  \n
        - Kuldip Trapasiya
        - Tanvi Gajera

    This plugin is used to send sms with the Twilio SMS Gateway for otp
    verification while signup and reset pasword for odoo account.

    To Configure:
        * Go to the Settings > General Settings.
        * Search for Twilio Settings.
        * Add the Twilio Details like: Account SID, Auth Token, Number From.
    twilio,
    signup,
    signin,
    reset,
    reset password,
    password reset,
    sms,
    otp,
    otp verification,
    signup otp verification,
    reset otp verification,
    reset password otp verification,
    mobile otp,
    phone otp,
    otp mobile,
    otp phone,

    signup,
    signin,
    reset,
    reset password,
    signup mobile,
    signup with mobile,
    signup with phone,
    signup with number,
    phone signup,
    mobile signup,
    signin mobile,
    signin with number,
    signin with mobile,
    signin with phone,
    phone signin,
    mobile signin,
    signin number,
    signup number,
    signin with number,
    signup with number,
    number signin,
    number signup
    """,
    "author": "Aktiv Software",
    "website": "https://www.aktivsoftware.com/",
    "category": "Tools",
    "version": "18.0.0.0.0",
    "depends": ["sms", "signup_with_phone"],
    "license": "OPL-1",
    "price": 10.00,
    "currency": "USD",
    "data": [
        "security/ir.model.access.csv",
        # "views/configuration.xml",
        "views/res_user_view.xml",
        "views/otp_template.xml",
        "views/april_configuration.xml",
        "data/otp_data_cleaner.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "signup_otp_twilio_sms/static/src/js/otp.js",
            "signup_otp_twilio_sms/static/src/css/button_style.css",
        ],
    },
    "images": ["static/description/banner.jpg"],
    "external_dependencies": {"python": ["twilio"]},
    "application": False,
    "installable": True,
    "active": True,
}

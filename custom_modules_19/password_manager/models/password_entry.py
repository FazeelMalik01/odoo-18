# -*- coding: utf-8 -*-

from markupsafe import Markup

from odoo import models, fields, api
from odoo.exceptions import AccessError

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None

NONE_LABEL = "—"


class PasswordEntry(models.Model):
    _name = "password.entry"
    _description = "Password Entry"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    url = fields.Char(tracking=True)
    username = fields.Char(tracking=True)
    password_encrypted = fields.Text() 
    notes = fields.Text(tracking=True)
    tag_ids = fields.Many2many(
        "password.entry.tag",
        string="Tags",
        relation="password_entry_tag_rel",
        column1="entry_id",
        column2="tag_id",
        tracking=True,
    )
    authorized_user_ids = fields.Many2many(
        "res.users",
        string="Authorized Users",
        relation="password_entry_authorized_user_rel",
        column1="entry_id",
        column2="user_id",
        tracking=True,
    )
    created_by = fields.Many2one(
        "res.users",
        string="Created By",
        default=lambda self: self.env.user,
        tracking=True,
    )


    password = fields.Char(
        string="Password",
        compute="_compute_password",
        inverse="_inverse_password",
        help="Enter password to save. Displayed masked for security.",
    )

    @api.depends("password_encrypted")
    def _compute_password(self):
        placeholder = "********"
        for rec in self:
            rec.password = placeholder if rec.password_encrypted else ""

    def _inverse_password(self):
        for rec in self:
            if not rec.password or rec.password == "********":
                continue
            rec.set_password(rec.password)

    def _creation_message(self):
        """Creation log: show '— → value' for each set field (like update tracking)."""
        self.ensure_one()
        doc_name = self.env["ir.model"]._get(self._name).name
        lines = ["%s created" % doc_name]
        
        entries = [
            (self._fields["name"].string, lambda r: r.name or ""),
            (self._fields["url"].string, lambda r: r.url or ""),
            (self._fields["username"].string, lambda r: r.username or ""),
            ("Password", lambda r: "********" if r.password_encrypted else ""),
            (self._fields["notes"].string, lambda r: r.notes or ""),
            (self._fields["tag_ids"].string, lambda r: ", ".join(r.tag_ids.mapped("name")) if r.tag_ids else ""),
            (self._fields["authorized_user_ids"].string, lambda r: ", ".join(r.authorized_user_ids.mapped("name")) if r.authorized_user_ids else ""),
            (self._fields["created_by"].string, lambda r: r.created_by.name if r.created_by else ""),
        ]
        for label, get_value in entries:
            value = get_value(self)
            if value:
                lines.append("%s: %s → %s" % (label, NONE_LABEL, value))
        
        return Markup("<br/>").join(Markup.escape(ln) for ln in lines)

    
    def _get_cipher(self):
        if Fernet is None:
            raise AccessError(
                "Missing Python library: pip install cryptography"
            )
        param = self.env["ir.config_parameter"].sudo()
        key = param.get_param("password_manager.secret_key")
        if not key:
            key = Fernet.generate_key().decode()
            param.set_param("password_manager.secret_key", key)
        return Fernet(key.encode())

    def set_password(self, password):
        if not password:
            self.password_encrypted = False
            return
        self.password_encrypted = self._get_cipher().encrypt(
            password.encode()
        ).decode()

    def _check_password_access(self):
        """Ensure current user is creator or in authorized users (does not override _check_access)."""
        self.ensure_one()
        user = self.env.user
        if user != self.created_by and user not in self.authorized_user_ids:
            raise AccessError("You are not allowed to access this password.")


    def action_reveal_password(self):
        self.ensure_one()
        self._check_password_access()
        if not self.password_encrypted:
            return ""
        password = self._get_cipher().decrypt(
            self.password_encrypted.encode()
        ).decode()
        self.message_post(
            body="🔓 Password revealed by %s" % self.env.user.name,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return password

    def action_copy_password(self):
        self.ensure_one()
        self._check_password_access()
        if not self.password_encrypted:
            return ""
        password = self._get_cipher().decrypt(
            self.password_encrypted.encode()
        ).decode()
        self.message_post(
            body="📋 Password copied to clipboard by %s" % self.env.user.name,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return password

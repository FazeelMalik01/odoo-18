from odoo import models, fields

class PasswordEntryTag(models.Model):
    _name = "password.entry.tag"
    _description = "Password Entry Tag"

    name = fields.Char(required=True)

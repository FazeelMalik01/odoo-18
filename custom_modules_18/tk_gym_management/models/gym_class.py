# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GymClass(models.Model):
    """Gym Class"""

    _name = "gym.class"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = __doc__
    _rec_name = "name"

    name = fields.Char()
    class_type_id = fields.Many2one("gym.class.types", string="Class for")
    trainer_ids = fields.Many2many(
        "hr.employee", string="Trainers", domain=[("is_trainer", "=", True)]
    )
    trainer_id = fields.Many2one(
        "hr.employee", domain=[("is_trainer", "=", True)]
    )
    tag_ids = fields.Many2many("gym.tag", string="Tags")
    class_type = fields.Selection(
        [("free", "Free"), ("paid", "Paid")], default="free"
    )
    start_date = fields.Datetime()
    end_date = fields.Datetime()
    cost = fields.Monetary(string="Charges")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id"
    )
    class_attendee_ids = fields.One2many("class.attendee", "yoga_class_id", string="Attendees")
    class_from = fields.Float(string="Class Timing")
    class_to = fields.Float()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("running", "Running"),
            ("complete", "Complete"),
            ("cancel", "Cancel"),
        ],
        default="draft",
        string="Status",
        copy=False,
    )

    @api.ondelete(at_uninstall=False)
    def _prevent_delete_record_if_status_not_draft(self):
        """ Prevent Delete Record if status is not draft """
        for rec in self:
            if rec.state != "draft":
                raise ValidationError(_("You can delete record only in draft state."))

    def action_running(self):
        """action running"""
        self._check_cost()
        self.state = "running"

    def action_complete(self):
        """action complete"""
        self.state = "complete"

    def action_cancel(self):
        """action cancel"""
        self.state = "cancel"

    @api.constrains("end_date", "start_date")
    def _check_end_date(self):
        """check end date"""
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date <= rec.start_date:
                raise ValidationError(_("End date cannot be earlier than the start date."))

    @api.constrains("class_from", "class_to")
    def _check_class_timing(self):
        """check class timing"""
        for rec in self:
            if rec.class_from < 0:
                raise ValidationError(_("Class timing cannot be negative."))
            if rec.class_from > 24 or rec.class_to > 24:
                raise ValidationError(_("Class timing cannot exceed 24 hours."))
            if rec.class_from == rec.class_to:
                raise ValidationError(_("Class start time and end time can not be the same."))
            if rec.class_to < rec.class_from:
                raise ValidationError(_("Class end time cannot be before than class start time."))

    @api.constrains("cost")
    def _check_cost(self):
        """check cost"""
        for rec in self:
            if rec.class_type == "paid" and rec.cost <= 0:
                raise ValidationError(_("Charges must be greater than zero."))


class GymClassAttendee(models.Model):
    """Gym Class Attendee"""

    _name = "class.attendee"
    _description = __doc__
    _rec_name = "member_id"

    member_id = fields.Many2one("res.partner", domain=[("is_member", "=", True)])
    invoice_id = fields.Many2one("account.move", copy=False)
    invoice_payment_state = fields.Selection(related="invoice_id.payment_state")
    yoga_class_id = fields.Many2one("gym.class", string="Class", ondelete="cascade")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id"
    )
    amount = fields.Monetary()

    @api.ondelete(at_uninstall=False)
    def _prevent_delete_record_if_invoiced(self):
        """ Prevent Invoiced record deleting """
        for rec in self:
            if rec.invoice_id:
                raise ValidationError(_("Invoiced record cannot be deleted."))

    @api.onchange("member_id")
    def onchange_member(self):
        """onchange member"""
        self.amount = self.yoga_class_id.cost

    def action_invoice(self):
        """action invoice"""
        data = {
            "product_id": self.env.ref("tk_gym_management.gym_yoga_classes").id,
            "name": self.yoga_class_id.name,
            "quantity": 1,
            "price_unit": self.amount,
        }
        invoice_line = [(0, 0, data)]
        record = {
            "partner_id": self.member_id.id,
            "invoice_date": date.today(),
            "invoice_line_ids": invoice_line,
            "move_type": "out_invoice",
            "yoga_class_invoice": True,
        }
        invoice_id = self.env["account.move"].sudo().create(record)
        self.invoice_id = invoice_id.id


class GymTag(models.Model):
    """Gym Tag"""

    _name = "gym.tag"
    _description = __doc__
    _rec_name = "name"

    name = fields.Char()
    color = fields.Integer(default=1)


class GymClassesTypes(models.Model):
    """Gym Classes Types"""

    _name = "gym.class.types"
    _description = __doc__

    name = fields.Char(string="Class Name")

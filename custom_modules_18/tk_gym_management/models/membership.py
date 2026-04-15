# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
import calendar
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta

class GymMemberInvoice(models.Model):
    """Gym Member Invoice"""

    _inherit = "account.move"
    _description = __doc__

    memberships_member_id = fields.Many2one("memberships.member", string="Membership")
    yoga_class_invoice = fields.Boolean(default=False)
    diet_plan_id = fields.Many2one("diet.plan")


class MembershipDetails(models.Model):
    """Gym Membership Type Details"""

    _inherit = "product.template"
    _description = __doc__

    is_membership = fields.Boolean()
    type = fields.Selection(default="service")
    membership_duration_id = fields.Many2one("membership.duration", string="Duration")
    tag_ids = fields.Many2many("gym.tag", string="Tags ")


class MembershipDuration(models.Model):
    """Membership Duration"""

    _name = "membership.duration"
    _description = __doc__

    name = fields.Char(string="Title")
    duration = fields.Integer(string="Durations")
    unit = fields.Char(default="Months")


class MembershipsDetails(models.Model):
    """Memberships Members Details"""

    _name = "memberships.member"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = __doc__
    _rec_name = "gym_membership_number"

    gym_membership_number = fields.Char(
        string="Membership No", readonly=True, default=lambda self: _("New"), copy=False
    )
    gym_member_id = fields.Many2one(
        "res.partner", string="Member", domain=[("is_member", "=", True)]
    )
    gym_membership_type_id = fields.Many2one("product.template", string="Membership Type")
    duration_id = fields.Many2one(
        "membership.duration", readonly=True, store=True
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id"
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        ondelete="cascade",
        readonly=True,
    )
    price = fields.Monetary(string="Charges")
    start_date = fields.Date(default=date.today())
    duration = fields.Integer(related="duration_id.duration", string="Membership Duration")
    end_date = fields.Date(compute="_compute_end_date", store=True)
    invoice_membership_id = fields.Many2one("account.move", string="Invoice", copy=False)

    # invoice status
    status_in_payment = fields.Selection(related="invoice_membership_id.status_in_payment")

    stages = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "In Progress"),
            ("expired", "Expired"),
            ("renewal", "Renew"),
            ("cancel", "Cancel"),
            ("close", "Close"),
        ],
        string="Status",
        default="draft",
        copy=False
    )

    renewed = fields.Boolean(default=False, copy=False)
    renewed_membership = fields.Many2one("memberships.member",
                                         copy=False)
    renewed_from = fields.Many2one("memberships.member", copy=False)

    # for not changing old membership duration
    old_end_date = fields.Date()
    base_end_date = fields.Date(string="Base End Date", compute="_compute_base_end_date", store=True)
    invoice_count = fields.Integer( string="Invoice Count", compute="_compute_invoice_count")
    freeze = fields.Boolean( string="Freeze Membership", default=False)
    freeze_duration_days = fields.Integer(string='Freeze Duration (Days)')
    freeze_extra_charges = fields.Monetary(string='Freeze Extra Charges')
    extended_end_date = fields.Date(string="Extended End Date", compute="_compute_extended_end_date", store=True)
    freeze_log_ids = fields.One2many('freeze.membership.log', 'membership_id', string='Freeze History')

    @api.depends('base_end_date', 'freeze_duration_days', 'freeze')
    def _compute_extended_end_date(self):
        for rec in self:
            if rec.freeze and rec.freeze_duration_days and rec.base_end_date:
                rec.extended_end_date = rec.base_end_date + timedelta(days=rec.freeze_duration_days)
            else:
                rec.extended_end_date = False

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = self.env["account.move"].search_count([
                ("memberships_member_id", "=", rec.id)
            ])

    def action_view_invoice(self):
        """Open linked invoices"""
        self.ensure_one()
        invoice_ids = self.env["account.move"].search([
            ("memberships_member_id", "=", self.id)
        ]).ids

        return {
            "type": "ir.actions.act_window",
            "name": "Invoices",
            "res_model": "account.move",
            "domain": [("id", "in", invoice_ids)],
            "view_mode": "list,form",
            "target": "current",
        }
    
    def action_open_freeze_wizard(self):
        """Called by the Freeze button — opens wizard instead of toggling directly"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Freeze Membership',
            'res_model': 'freeze.membership.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_membership_id': self.id,
            }
        }

    @api.ondelete(at_uninstall=False)
    def _prevent_unlink_status_and_invoice_wise(self):
        """ Prevent unlink status and invoice wise """
        for rec in self:
            if rec.stages in ["close", "expired", "active", "renewal"]:
                raise ValidationError(
                    _(
                        "You are not allowed to delete records that are in the close, expired, "
                        "in progress, or renewal stages."
                    )
                )
            if rec.stages == "cancel":
                if rec.invoice_membership_id.state == "posted":
                    raise ValidationError(
                        _("A record of whose invoice has been posted cannot be deleted.")
                    )

    @api.depends('start_date', 'duration')
    def _compute_base_end_date(self):
        for rec in self:
            if rec.duration and rec.start_date:
                rec.base_end_date = rec.start_date + relativedelta(months=rec.duration)
            else:
                rec.base_end_date = False

    @api.depends('base_end_date', 'extended_end_date', 'freeze')
    def _compute_end_date(self):
        for rec in self:
            if rec.freeze and rec.extended_end_date:
                rec.end_date = rec.extended_end_date
            else:
                rec.end_date = rec.base_end_date

    def action_cancel(self):
        """action cancel"""
        self.stages = "cancel"

    def draft_to_active(self):
        """draft to active"""
        self.stages = "active"
        self.action_invoice()

    def active_to_expiry(self):
        """active to expiry"""
        self.stages = "expired"

    @api.onchange("gym_membership_type_id", "duration_id")
    def membership_type_price_get(self):
        """membership type price get"""
        for rec in self:
            if rec.gym_membership_type_id:
                rec.price = rec.gym_membership_type_id.list_price
                rec.duration_id = rec.gym_membership_type_id.membership_duration_id

    @api.model_create_multi
    def create(self, vals_list):
        """create method"""
        for vals in vals_list:
            if vals.get("gym_membership_number", _("New")) == _("New"):
                vals["gym_membership_number"] = self.env["ir.sequence"].next_by_code(
                    "rest.seq.member"
                ) or _("New")
        res = super().create(vals_list)
        return res

    def action_invoice(self):
        """action invoice"""
        data = {
            "product_id": self.gym_membership_type_id.product_variant_id.id,
            "quantity": 1,
            "price_unit": self.price,
        }
        invoice_line = [(0, 0, data)]
        record = {
            "partner_id": self.gym_member_id.id,
            "invoice_date": date.today(),
            "invoice_line_ids": invoice_line,
            "move_type": "out_invoice",
            "memberships_member_id": self.id,
        }
        invoice_id = self.env["account.move"].sudo().create(record)
        self.invoice_membership_id = invoice_id.id
        return {
            "type": "ir.actions.act_window",
            "name": "Invoice",
            "res_model": "account.move",
            "res_id": invoice_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # Schedular
    @api.model
    def expire_membership_after_end_date(self):
        """expire membership after end date"""
        membership_records = self.env["memberships.member"].search([("stages", "=", "active")])
        today = fields.Date.today()
        for rec in membership_records:
            if rec.end_date < today:
                rec.write({"stages": "expired"})

    @api.model
    def send_reminder_membership_renewal(self):
        """send reminder membership renewal"""
        membership_records = self.env["memberships.member"].search([("stages", "=", "active")])
        today = fields.Date.today()
        reminder_days = (
            self.env["ir.config_parameter"].sudo().get_param("tk_gym_management.reminder_days")
        )
        mail_template = self.env.ref(
            "tk_gym_management.membership_expiring_reminder_mail_template"
        ).sudo()
        for rec in membership_records:
            if int((rec.end_date - today).days) == int(reminder_days) and mail_template:
                mail_template.send_mail(rec.id, force_send=True)

    @api.model
    def get_gym_stats(self):
        """get gym stats"""
        members = (self.env["res.partner"].sudo().search_count([("is_member", "=", True)]),)
        memberships = (self.env["memberships.member"].sudo().search_count([]),)
        equipments = (self.env["gym.equipment"].sudo().search_count([]),)
        workout = (self.env["gym.workout"].sudo().search_count([]),)
        exercise = (self.env["gym.exercise"].sudo().search_count([]),)
        classes = (self.env["gym.class"].sudo().search_count([]),)
        daily_attendance = (
            [self.attendance_date(), self.employee_attendance(), self.member_attendance()],
        )

        data = {
            "gym_members": members,
            "gym_memberships": memberships,
            "gym_equipments": equipments,
            "gym_workouts": workout,
            "gym_exercises": exercise,
            "gym_classes": classes,
            "get_membership": self.get_membership(),
            "membershipperson": self.membershipperson(),
            "daily_attendance": daily_attendance,
            "invoice": self.get_month_invoice(),
        }
        return data

    def get_membership(self):
        """get membership"""
        membership, membership_counts, data_cat = [], [], []
        membership_ids = self.env["product.template"].search([("is_membership", "=", True)])
        if not membership_ids:
            data_cat = [[], []]
        for stg in membership_ids:
            membership_data = self.env["memberships.member"].search_count(
                [("gym_membership_type_id", "=", stg.id), ("stages", "=", "active")]
            )
            membership_counts.append(membership_data)
            membership.append(stg.name)
        data_cat = [membership, membership_counts]
        return data_cat

    def membershipperson(self):
        """membership person"""
        membership, membership_counts, membership_counts_f, data_cat = [], [], [], []
        membership_ids = self.env["product.template"].search([("is_membership", "=", True)])
        if not membership_ids:
            data_cat = [[], []]
        for stg in membership_ids:
            membership_data = self.env["memberships.member"].search_count(
                [("gym_membership_type_id", "=", stg.id), ("gym_member_id.gender", "=", "m")]
            )
            membership_f = self.env["memberships.member"].search_count(
                [("gym_membership_type_id", "=", stg.id), ("gym_member_id.gender", "=", "f")]
            )
            membership_counts_f.append(membership_f)
            membership_counts.append(membership_data)
            membership.append(stg.name)
        data_cat = [membership, membership_counts, membership_counts_f]
        return data_cat

    def attendance_date(self):
        """attendance date"""
        day_dict = {}
        year = fields.date.today().year
        month = fields.date.today().month
        num_days = calendar.monthrange(year, month)[1]
        days = [date(year, month, day) for day in range(1, num_days + 1)]
        for data in days:
            day_dict[data.strftime("%d") + " " + data.strftime("%h")] = 0
        return list(day_dict.keys())

    def employee_attendance(self):
        """employee attendance"""
        day_dict = {}
        year = fields.date.today().year
        month = fields.date.today().month
        num_days = calendar.monthrange(year, month)[1]
        days = [date(year, month, day) for day in range(1, num_days + 1)]
        for data in days:
            day_dict[data.strftime("%d") + " " + data.strftime("%h")] = 0
        attendance = self.env["employee.attendance"].search([])
        for data in attendance:
            if data.check_in.year == year and month == data.check_in.month:
                attendance_time = data.check_in.strftime("%d") + " " + data.check_in.strftime("%h")
                day_dict[attendance_time] = day_dict[attendance_time] + 1
        return list(day_dict.values())

    def member_attendance(self):
        """member attendance"""
        day_dict = {}
        year = fields.date.today().year
        month = fields.date.today().month
        num_days = calendar.monthrange(year, month)[1]
        days = [date(year, month, day) for day in range(1, num_days + 1)]
        for data in days:
            day_dict[data.strftime("%d") + " " + data.strftime("%h")] = 0
        attendance = self.env["member.attendance"].search([])
        for data in attendance:
            if data.check_in.year == year and month == data.check_in.month:
                attendance_time = data.check_in.strftime("%d") + " " + data.check_in.strftime("%h")
                day_dict[attendance_time] = day_dict[attendance_time] + 1
        return list(day_dict.values())

    def get_month_invoice(self):
        """get month invoice"""
        year = fields.date.today().year
        bill_dict = {
            "January": 0,
            "February": 0,
            "March": 0,
            "April": 0,
            "May": 0,
            "June": 0,
            "July": 0,
            "August": 0,
            "September": 0,
            "October": 0,
            "November": 0,
            "December": 0,
        }
        bill = (
            self.env["account.move"]
            .sudo()
            .search(
                ["|", ("memberships_member_id", "!=", False), ("yoga_class_invoice", "!=", False)]
            )
        )
        for data in bill:
            if data.invoice_date:
                if data.invoice_date.year == year:
                    bill_dict[data.invoice_date.strftime("%B")] = (
                            bill_dict[data.invoice_date.strftime("%B")] + data.amount_total
                    )
        return [list(bill_dict.keys()), list(bill_dict.values())]

class FreezeMembershipLog(models.Model):
    _name = 'freeze.membership.log'
    _description = 'Freeze Membership Log'

    membership_id = fields.Many2one('memberships.member', string='Membership')
    freeze_date = fields.Date(string='Freeze Date', default=fields.Date.today)
    duration_days = fields.Integer(string='Duration (Days)')
    extra_charges = fields.Monetary(string='Extra Charges')
    currency_id = fields.Many2one(
        'res.currency', related='membership_id.currency_id'
    )
    extended_end_date = fields.Date(string="Extended End Date")
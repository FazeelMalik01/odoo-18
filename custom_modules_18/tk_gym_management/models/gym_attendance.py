# -*- coding: utf-8 -*-
# Copyright 2020-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GymEmployeeAttendance(models.Model):
    """Gym Employee Attendance"""
    _name = 'employee.attendance'
    _description = __doc__
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', domain=[('is_trainer', '=', True)])
    check_in = fields.Datetime(default=datetime.today())
    check_out = fields.Datetime(readonly=True, store=True)
    working_hours_per_day = fields.Float(related='employee_id.working_hours_per_day')
    employee_attendance_line_ids = fields.One2many('employee.attendance.lines',
                                                   'employee_attendance_id',
                                                   string='Employee Attendance Lines')
    total_hours = fields.Float(compute='_compute_total_hours')
    attended_hours = fields.Float(compute='_compute_attended_hours')

    @api.depends('employee_attendance_line_ids', 'working_hours_per_day')
    def _compute_total_hours(self):
        """compute total hours"""
        for rec in self:
            total = len(rec.employee_attendance_line_ids) * rec.working_hours_per_day
            rec.total_hours = total

    @api.depends('employee_attendance_line_ids')
    def _compute_attended_hours(self):
        """compute attended hours"""
        for rec in self:
            hours = 0.0
            for record in rec.employee_attendance_line_ids:
                hours += record.hours
            rec.attended_hours = hours

    def check_out_employee(self):
        """check out employee"""
        self.check_out = fields.datetime.today()

    def action_pass(self):
        """action pass"""
        return


class EmployeeAttendanceLines(models.Model):
    """Employee Attendance Lines"""
    _name = 'employee.attendance.lines'
    _description = __doc__
    _rec_name = 'employee_attendance_id'

    employee_attendance_id = fields.Many2one('employee.attendance')
    check_in = fields.Datetime(default=datetime.now())
    check_out = fields.Datetime()
    hours = fields.Float()
    working_hours_per_day = fields.Float(related='employee_attendance_id.working_hours_per_day')
    state = fields.Selection(
        [('new', 'New'), ('checked_in', 'Checked In'), ('checked_out', 'Checked Out')],
        default='new', copy=False, string='Status')
    complete_hours = fields.Boolean()
    incomplete_hours = fields.Boolean()

    @api.ondelete(at_uninstall=False)
    def _prevent_deleting_record_if_checked_out(self):
        """ Prevent Deleting Record if checked out """
        for rec in self:
            if rec.state == 'checked_out':
                raise ValidationError(_('When a record is checked out, it cannot be deleted.'))

    def check_in_employee(self):
        """check in employee"""
        self.state = 'checked_in'
        self.check_in = fields.Datetime.now()

    def check_out_datetime_employee(self):
        """check out datime employee"""
        self.check_out = fields.Datetime.now()
        total_hours = round((self.check_out - self.check_in).total_seconds() / 3600, 2)
        if total_hours < 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Warning"),

                    'type': 'warning',
                    'message': _("Check-in time cannot be greater than check-out time."),

                }
            }
        self.hours = total_hours
        self.state = 'checked_out'
        if total_hours >= self.working_hours_per_day:
            self.complete_hours = True
            self.incomplete_hours = False
        elif total_hours < self.working_hours_per_day:
            self.complete_hours = False
            self.incomplete_hours = True


class GymMemberAttendance(models.Model):
    """Gym Member Attendance"""
    _name = 'member.attendance'
    _description = __doc__
    _rec_name = 'member_id'

    member_id = fields.Many2one('res.partner', domain=[('is_member', '=', True)])
    check_in = fields.Datetime(default=datetime.today())
    check_out = fields.Datetime(readonly=True, store=True)
    gym_hours_per_day = fields.Float(related='member_id.gym_hours_per_day')
    member_attendance_line_ids = fields.One2many('member.attendance.lines', 'member_attendance_id')
    total_hours = fields.Float(compute='_compute_total_hours')
    attended_hours = fields.Float(compute='_compute_attended_hours')

    @api.depends('member_attendance_line_ids', 'gym_hours_per_day')
    def _compute_total_hours(self):
        """compute total hours"""
        for rec in self:
            total = len(rec.member_attendance_line_ids) * rec.gym_hours_per_day
            rec.total_hours = total

    @api.depends('member_attendance_line_ids')
    def _compute_attended_hours(self):
        """compute attended hours"""
        for rec in self:
            hours = 0.0
            for record in rec.member_attendance_line_ids:
                hours += record.hours
            rec.attended_hours = hours

    def check_out_member(self):
        """check out member"""
        self.check_out = fields.datetime.today()

    def action_pass(self):
        """action pass"""
        return


class MemberAttendanceLines(models.Model):
    """Member Attendance Lines"""
    _name = 'member.attendance.lines'
    _description = __doc__
    _rec_name = 'member_attendance_id'

    member_attendance_id = fields.Many2one('member.attendance')
    check_in = fields.Datetime(default=datetime.now())
    check_out = fields.Datetime()
    hours = fields.Float()
    gym_hours_per_day = fields.Float(related='member_attendance_id.gym_hours_per_day')
    state = fields.Selection(
        [('new', 'New'), ('checked_in', 'Checked In'), ('checked_out', 'Checked Out')],
        default='new', copy=False, string="Status")
    complete_hours = fields.Boolean()
    incomplete_hours = fields.Boolean()

    @api.ondelete(at_uninstall=False)
    def _prevent_deleting_record_if_checked_out(self):
        """ Prevent Deleting Record if checked out """
        for rec in self:
            if rec.state == 'checked_out':
                raise ValidationError(_('When a record is checked out, it cannot be deleted.'))

    def check_in_member(self):
        """check in member"""
        self.state = 'checked_in'
        self.check_in = fields.Datetime.now()

    def check_out_datetime_member(self):
        """check out datetime member"""
        self.check_out = fields.Datetime.now()
        total_hours = round((self.check_out - self.check_in).total_seconds() / 3600, 2)
        if total_hours < 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Warning"),

                    'type': 'warning',
                    'message': _("Check-in time cannot be greater than check-out time."),

                }
            }
        self.hours = total_hours
        self.state = 'checked_out'
        if total_hours >= self.gym_hours_per_day:
            self.complete_hours = True
            self.incomplete_hours = False
        elif total_hours < self.gym_hours_per_day:
            self.complete_hours = False
            self.incomplete_hours = True

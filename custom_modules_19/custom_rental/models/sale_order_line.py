# -*- coding: utf-8 -*-

from math import ceil

from odoo import _, api, fields, models
from odoo.tools import format_datetime, format_time
from pytz import UTC, timezone


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Per-line rental period (override sale_renting's related fields so each line can have its own period)
    start_date = fields.Datetime(
        string='Rental Start Date',
        copy=True,
        help='Start date for this line. Defaults from order when the line is created.',
    )
    return_date = fields.Datetime(
        string='Rental Return Date',
        copy=True,
        help='Return date for this line. Defaults from order when the line is created.',
    )
    duration_days = fields.Integer(
        string='Duration (days)',
        compute='_compute_line_duration',
        store=True,
        help='Rental duration in days for this line.',
    )
    remaining_hours = fields.Integer(
        string='Remaining (hours)',
        compute='_compute_line_duration',
        store=True,
        help='Remaining hours of the rental period for this line.',
    )
    duration_hours = fields.Integer(
        string='Duration (hours)',
        compute='_compute_line_duration',
        store=True,
        help='Total rental duration in hours for this line.',
    )

    @api.depends('start_date', 'return_date')
    def _compute_line_duration(self):
        for line in self:
            if line.start_date and line.return_date and line.return_date > line.start_date:
                delta = line.return_date - line.start_date
                line.duration_days = delta.days
                line.remaining_hours = ceil(delta.seconds / 3600)
                line.duration_hours = delta.days * 24 + line.remaining_hours
            else:
                line.duration_days = 0
                line.remaining_hours = 0
                line.duration_hours = 0

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order_id = res.get('order_id') or self.env.context.get('default_order_id')
        if order_id and ('start_date' in fields_list or 'return_date' in fields_list):
            order = self.env['sale.order'].browse(order_id)
            if order.exists():
                if 'start_date' in fields_list and not res.get('start_date'):
                    res['start_date'] = order.rental_start_date
                if 'return_date' in fields_list and not res.get('return_date'):
                    res['return_date'] = order.rental_return_date
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order_id = vals.get('order_id')
            if order_id and ('start_date' not in vals or 'return_date' not in vals):
                order = self.env['sale.order'].browse(order_id)
                if order.exists():
                    if 'start_date' not in vals and order.rental_start_date:
                        vals['start_date'] = order.rental_start_date
                    if 'return_date' not in vals and order.rental_return_date:
                        vals['return_date'] = order.rental_return_date
        return super().create(vals_list)

    @api.depends('start_date')
    def _compute_reservation_begin(self):
        """Use line's own start_date for reservation begin (per-line period)."""
        lines = self.filtered('is_rental')
        for line in lines:
            line.reservation_begin = line.start_date
        (self - lines).reservation_begin = False

    def _get_rental_order_line_description(self):
        """Use this line's start_date and return_date for the description."""
        tz = self._get_tz()
        start_date = self.start_date
        return_date = self.return_date
        env = self.with_context(use_babel=True).env
        if not start_date or not return_date:
            return ''
        if (
            start_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date()
            == return_date.replace(tzinfo=UTC).astimezone(timezone(tz)).date()
        ):
            return_date_part = format_time(env, return_date, tz=tz, time_format='short')
        else:
            return_date_part = format_datetime(env, return_date, tz=tz, dt_format='short')
        start_date_part = format_datetime(env, start_date, tz=tz, dt_format='short')
        return _(
            "\n%(from_date)s to %(to_date)s",
            from_date=start_date_part,
            to_date=return_date_part,
        )

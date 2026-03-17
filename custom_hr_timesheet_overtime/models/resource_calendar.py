# -*- coding: utf-8 -*-

##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016 - now Bytebrand Outsourcing AG (<http://www.bytebrand.net>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import datetime as dtime

from datetime import datetime, timedelta, date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import pytz
import logging

_logger = logging.getLogger(__name__)


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def get_working_intervals_of_day(self, start_dt=None, end_dt=None,
                                     leaves=None, compute_leaves=False,
                                     resource_id=None, default_interval=None):
        if start_dt is None and end_dt is not None:
            start_dt = end_dt.replace(hour=0, minute=0, second=0)
        elif start_dt is None:
            start_dt = datetime.now().replace(hour=0, minute=0, second=0)

        if end_dt is None:
            end_dt = start_dt.replace(hour=23, minute=59, second=59)

        assert start_dt.date() == end_dt.date(), \
            'get_working_intervals_of_day is restricted to one day'

        intervals = []
        work_dt = start_dt.replace(hour=0, minute=0, second=0)

        # No calendar: return empty (no default_interval support without
        # _interval_new which no longer exists in Odoo 18)
        if not self.ids:
            return intervals

        for calendar_working_day in self.get_attendances_for_weekdays(
                [start_dt.weekday()], start_dt, end_dt):

            str_time_from_dict = str(calendar_working_day.hour_from).split('.')
            hour_from = int(str_time_from_dict[0])
            if int(str_time_from_dict[1]) < 10:
                minutes_from = int(60 * int(str_time_from_dict[1]) / 10)
            elif int(str_time_from_dict[1]) > 100:
                m = str_time_from_dict[1][:2] + '.' + str_time_from_dict[1][2:]
                minutes_from = round(60 * float(m) / 100)
            else:
                minutes_from = int(60 * int(str_time_from_dict[1]) / 100)

            str_time_to_dict = str(calendar_working_day.hour_to).split('.')
            hour_to = int(str_time_to_dict[0])
            if int(str_time_to_dict[1]) < 10:
                minutes_to = int(60 * int(str_time_to_dict[1]) / 10)
            elif int(str_time_to_dict[1]) > 100:
                m = str_time_to_dict[1][:2] + '.' + str_time_to_dict[1][2:]
                minutes_to = round(60 * float(m) / 100)
            else:
                minutes_to = int(60 * int(str_time_to_dict[1]) / 100)

            working_interval = (
                work_dt.replace(hour=hour_from, minute=minutes_from),
                work_dt.replace(hour=hour_to, minute=minutes_to),
            )
            intervals.append(working_interval)

        return intervals

    def get_working_hours_of_date(self, start_dt=None, end_dt=None,
                                  leaves=None, compute_leaves=None,
                                  resource_id=None, default_interval=None):
        """Get the working hours of the day based on calendar."""
        res = dtime.timedelta()
        intervals = self.get_working_intervals_of_day(
            start_dt, end_dt, leaves, compute_leaves,
            resource_id, default_interval)
        for interval in intervals:
            res += interval[1] - interval[0]
        return seconds(res) / 3600.0

    def get_bonus_hours_of_date(self, start_dt=None, end_dt=None,
                                leaves=None, compute_leaves=False,
                                resource_id=None, default_interval=None):
        """Get the working hours of the day based on calendar."""
        res = dtime.timedelta()
        intervals = self.get_working_intervals_of_day(
            start_dt, end_dt, leaves, compute_leaves,
            resource_id, default_interval)
        for interval in intervals:
            res += interval[1] - interval[0]
        return seconds(res) / 3600.0

    def get_attendances_for_weekdays(self, weekdays, start_dt, end_dt):
        """Given a list of weekdays, return matching resource.calendar.attendance"""
        res = []
        for att in self.attendance_ids:
            if int(att.dayofweek) in weekdays:
                if not att.date_from or not att.date_to:
                    res.append(att)
                else:
                    date_from = att.date_from
                    date_to = att.date_to
                    if date_from <= start_dt.date() <= date_to:
                        res.append(att)
        return res

    use_overtime = fields.Boolean(string="Use Overtime Setting")
    min_overtime_count = fields.Integer(
        string="Minimum overtime days",
        default=0,
        required=True,
    )
    count = fields.Integer(
        string="Percent Count",
        default=0,
        required=True,
    )
    overtime_attendance_ids = fields.One2many(
        'resource.calendar.attendance.overtime',
        'overtime_calendar_id',
        string='Overtime',
    )
    two_days_shift = fields.Boolean(
        string='Shift between two days',
        default=True,
        help='Use for night shift between two days.',
    )

    @api.constrains('min_overtime_count')
    def _check_min_overtime_count(self):
        if self.min_overtime_count < 0:
            raise ValidationError("Minimum overtime days must be positive.")

    @api.constrains('two_days_shift')
    def _check_two_days_shift(self):
        if self.two_days_shift is False:
            for attendance_id in self.overtime_attendance_ids:
                if attendance_id.hour_to <= attendance_id.hour_from:
                    raise ValidationError(
                        "Overtime to must be greater than overtime from "
                        "when two days shift is not using.")

    def initial_overtime(self):
        contracts = self.env['hr.contract'].search(
            [('resource_calendar_id', '=', self.id)])
        employee_ids = [contract.employee_id.id for contract in contracts]
        for employee in self.env['hr.employee'].browse(set(employee_ids)):
            employee.initial_overtime()


class ResourceCalendarAttendanceOvertime(models.Model):
    _name = "resource.calendar.attendance.overtime"
    _order = 'dayofweek, hour_from'
    _description = 'ResourceCalendarAttendanceOvertime'

    name = fields.Char(required=True)
    dayofweek = fields.Selection(
        [('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'),
         ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'),
         ('6', 'Sunday')],
        string='Day of Week',
        required=True,
        index=True,
        default='0',
    )
    date_from = fields.Date(string='Starting Date')
    date_to = fields.Date(string='End Date')
    hour_from = fields.Float(
        string='Overtime from',
        required=True,
        index=True,
        help="Start and End time of Overtime.",
    )
    hour_to = fields.Float(string='Overtime to', required=True)
    overtime_calendar_id = fields.Many2one(
        "resource.calendar",
        string="Resource's Calendar",
        required=True,
        ondelete='cascade',
    )


def seconds(td):
    assert isinstance(td, dtime.timedelta)
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10. ** 6


def to_tz(dt, tz_name):
    tz = pytz.timezone(tz_name)
    return pytz.UTC.localize(dt.replace(tzinfo=None),
                             is_dst=False).astimezone(tz).replace(tzinfo=None)


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    def write(self, values):
        res = super(ResourceCalendarAttendance, self).write(values)
        if 'date_from' in values or 'date_to' in values:
            self.change_working_time(None, None)
        return res

    @api.model
    def create(self, values):
        res = super(ResourceCalendarAttendance, self).create(values)
        res.change_working_time(None, None)
        return res

    def unlink(self):
        res = super(ResourceCalendarAttendance, self).unlink()
        return res

    def change_working_time(self, date_start, date_end,
                            resource_calendar_id=False):
        return

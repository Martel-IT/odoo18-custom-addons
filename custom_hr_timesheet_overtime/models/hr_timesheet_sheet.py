# -*- coding: utf-8 -*-

##############################################################################
#
#    Clear Groups for Odoo
#    Copyright (C) 2016 Bytebrand GmbH (<http://www.bytebrand.net>).
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

import math

from datetime import datetime, timedelta, time, date
from odoo import api, fields, models, _
from dateutil import rrule, parser
import logging

_logger = logging.getLogger(__name__)


def float_time_convert(float_val):
    """
    Converts float value of hours into time value
    :param float_val: hours/minutes in float type
    :return: string
    """
    hours = math.floor(abs(float_val))
    mins = abs(float_val) - hours
    mins = round(mins * 60)
    if mins >= 60.0:
        hours += 1
        mins = 0.0
    float_time = '%02d:%02d' % (hours, mins)
    return float_time


def sign_float_time_convert(float_time):
    sign = '-' if float_time < 0 else ''
    return sign + float_time_convert(float_time)


class Sheet(models.Model):
    """
        Addition plugin for HR timesheet for work with duty hours
    """
    _name = "hr_timesheet.sheet"
    _inherit = 'hr_timesheet.sheet'

    # Remains as cache of the total_duty_hours.
    total_duty_hours = fields.Float(
        string='Total Duty Hours (temp)',
        compute='_duty_hours',
        default=0.0,
    )
    total_duty_hours_done = fields.Float(
        string='Total Duty Hours (stored)',
        readonly=True,
        default=0.0,
    )
    total_diff_hours = fields.Float(
        string='Total Diff Hours',
        readonly=True,
        default=0.0,
    )
    # Running balance: worked - duty + previous balance
    calculate_diff_hours = fields.Float(
        compute='_calculate_diff_hours',
        string="Diff (worked-duty)",
    )
    # Delta from the previous month
    prev_timesheet_diff = fields.Float(
        compute='_prev_timesheet_diff',
        string="Previous overtime",
    )
    # HTML table for "Flexitime Analysis" tab
    analysis = fields.Text(
        compute='_get_analysis',
        string="Attendance Analysis",
    )

    @api.depends("timesheet_ids.unit_amount")
    def _compute_total_time(self):
        for sheet in self:
            total_time = 0
            for aal in sheet.timesheet_ids:
                total_time += aal.unit_amount
            sheet.total_time = total_time

    def _duty_hours(self):
        for sheet in self:
            if sheet.state == 'done' and sheet.total_duty_hours_done:
                sheet.total_duty_hours = sheet.total_duty_hours_done
            else:
                total_duty_hours = 0.0
                dates = list(rrule.rrule(rrule.DAILY,
                                         dtstart=sheet.date_start,
                                         until=sheet.date_end))
                period = {'date_start': sheet.date_start,
                          'date_end': sheet.date_end}
                for date_line in dates:
                    total_duty_hours += sheet.calculate_duty_hours(
                        date_start=date_line,
                        period=period,
                    )
                sheet.total_duty_hours = total_duty_hours

    def count_leaves(self, date_start, employee_id, period):
        holiday_obj = self.env['hr.leave']
        start_leave_period = end_leave_period = False
        if period.get('date_start') and period.get('date_end'):
            start_leave_period = period.get('date_start')
            end_leave_period = period.get('date_end')
        holiday_ids = holiday_obj.search(
            ['|', '&',
             ('date_from', '>=', start_leave_period),
             ('date_from', '<=', end_leave_period),
             '&', ('date_to', '<=', end_leave_period),
             ('date_to', '>=', start_leave_period),
             ('employee_id', '=', employee_id),
             ('state', '=', 'validate')])
        leaves = []
        for leave in holiday_ids:
            leave_date_start = leave.date_from
            leave_date_end = leave.date_to
            leave_dates = list(rrule.rrule(rrule.DAILY,
                                           dtstart=leave.date_from,
                                           until=leave.date_to))
            for leave_date in leave_dates:
                if leave_date.strftime('%Y-%m-%d') == date_start.strftime('%Y-%m-%d'):
                    leaves.append(
                        (leave_date_start, leave_date_end, leave.number_of_days))
                    break
        return leaves

    def get_overtime(self, start_date):
        for sheet in self:
            return sheet.total_time - sheet.total_duty_hours

    def _prev_timesheet_diff(self):
        for sheet in self:
            old_timesheet_start_from = sheet.date_start - timedelta(days=1)
            prev_timesheet_diff = self.get_previous_month_diff(
                sheet.employee_id.id,
                old_timesheet_start_from.strftime('%Y-%m-%d'),
            )
            sheet.prev_timesheet_diff = prev_timesheet_diff

    def _get_analysis(self):
        for sheet in self:
            data = self.attendance_analysis(sheet.id, function_call=True)
            keys = (_('Date'), _('Running'), _('Duty Hours'), _('Worked Hours'),
                    _('Difference'))
            output = [
                '<style>'
                '.attendanceTable td, .attendanceTable th {padding: 3px; border: 1px solid #C0C0C0;'
                'border-collapse: collapse;'
                'text-align: right;}'
                '.attendanceTable {font-family: "system-ui" !important; border-spacing: 2px;'
                'font-size: 1rem;'
                'width: 100%;'
                'border: 1px solid #C0C0C0; border-collapse: collapse;}</style>'
                '<table class="attendanceTable">',
            ]
            if 'previous_month_diff' in data:
                if isinstance(data['previous_month_diff'], (int, float)):
                    output.append('<tr>')
                    prev_ts = _('Previous Timesheet:')
                    output.append('<th colspan="2">' + prev_ts + ' </th>')
                    output.append('<td colspan="3">' + str(sign_float_time_convert(data['previous_month_diff'])) + '</td>')
                    output.append('</tr>')
            output.append('<tr>')
            for th in keys:
                output.append('<th>' + th + '</th>')
            output.append('</tr>')
            if 'hours' in data and data['hours']:
                if isinstance(data['hours'], list):
                    for row in data['hours']:
                        output.append('<tr>')
                        for th in keys:
                            output.append('<td>' + row.get(th, '') + '</td>')
                        output.append('</tr>')
            output.append('<tr>')
            total_ts = _('Total:')
            output.append('<th>' + total_ts + ' </th>')
            if 'total' in data and data['total']:
                if isinstance(data['total'], dict):
                    for v in keys:
                        if data['total'].get(v):
                            output.append('<td>' + '%s' % sign_float_time_convert(data['total'].get(v)) + '</td>')
            output.append('</tr>')
            output.append('</table>')
            sheet['analysis'] = '\n'.join(output)

    def calculate_duty_hours(self, date_start, period):
        contract_obj = self.env['hr.contract']
        duty_hours = 0.0
        contract_ids = contract_obj.search(
            [('employee_id', '=', self.employee_id.id),
             ('date_start', '<=', date_start), '|',
             ('date_end', '>=', date_start),
             ('date_end', '=', None)])
        for contract in contract_ids:
            if contract:
                # date_start from rrule is a datetime; pass it directly
                start_dt = date_start if isinstance(date_start, datetime) else datetime(
                    date_start.year, date_start.month, date_start.day)
                dh = contract.resource_calendar_id.get_working_hours_of_date(
                    start_dt=start_dt,
                    resource_id=self.employee_id.id)
            else:
                dh = 0.0
            leaves = self.count_leaves(date_start, self.employee_id.id, period)
            if not leaves:
                if not dh:
                    dh = 0.0
                duty_hours += dh
            else:
                if leaves[-1] and leaves[-1][-1]:
                    if float(leaves[-1][-1]) == 0.5:
                        duty_hours += dh / 2
        return duty_hours

    def get_previous_month_diff(self, employee_id, prev_timesheet_date_from):
        total_diff = 0.0
        prev_timesheet_ids = self.search(
            [('employee_id', '=', employee_id)]
        ).filtered(lambda sheet: sheet.date_end < self.date_start).sorted(
            key=lambda v: v.date_start)
        if prev_timesheet_ids:
            total_diff = prev_timesheet_ids[-1].calculate_diff_hours
        return total_diff

    def _calculate_diff_hours(self):
        for sheet in self:
            if sheet.state == 'done' and sheet.total_diff_hours:
                sheet.calculate_diff_hours = sheet.total_diff_hours
            else:
                sheet.calculate_diff_hours = (
                    self.get_overtime(datetime.today().strftime('%Y-%m-%d')) +
                    sheet.prev_timesheet_diff)

    def _get_user_datetime_format(self):
        """ Get user's language & fetch date/time formats of that language """
        lang_obj = self.env['res.lang']
        language = self.env.user.lang
        lang_ids = lang_obj.search([('code', '=', language)])
        date_format = '%Y-%m-%d'
        time_format = '%H:%M:%S'
        for lang in lang_ids:
            date_format = lang.date_format
            time_format = lang.time_format
        return date_format, time_format

    def attendance_analysis(self, timesheet_id=None, function_call=False):
        date_format, time_format = self._get_user_datetime_format()
        for sheet in self:
            if sheet.id == timesheet_id:
                employee_id = sheet.employee_id.id
                start_date = sheet.date_start
                end_date = sheet.date_end
                previous_month_diff = self.get_previous_month_diff(
                    employee_id, start_date)
                current_month_diff = previous_month_diff
                res = {
                    'previous_month_diff': previous_month_diff,
                    'hours': []
                }
                period = {'date_start': start_date, 'date_end': end_date}
                dates = list(rrule.rrule(rrule.DAILY,
                                         dtstart=start_date,
                                         until=end_date))
                work_current_month_diff = 0.0
                if function_call:
                    total = {
                        _('Worked Hours'): 0.0,
                        _('Duty Hours'): 0.0,
                        _('Running'): current_month_diff,
                        _('Difference'): 0.0,
                    }
                else:
                    total = {
                        'worked_hours': 0.0,
                        'duty_hours': 0.0,
                        'diff': current_month_diff,
                        'work_current_month_diff': 0.0,
                    }
                for date_line in dates:
                    dh = sheet.calculate_duty_hours(date_start=date_line, period=period)
                    worked_hours = 0.0
                    for att in sheet.timesheet_ids:
                        if att.date == date_line.date():
                            worked_hours += att.unit_amount

                    diff = worked_hours - dh
                    current_month_diff += diff
                    work_current_month_diff += diff
                    if function_call:
                        res['hours'].append({
                            _('Date'): date_line.strftime(date_format),
                            _('Running'): sign_float_time_convert(current_month_diff),
                            _('Duty Hours'): sign_float_time_convert(dh),
                            _('Worked Hours'): sign_float_time_convert(worked_hours),
                            _('Difference'): sign_float_time_convert(diff),
                        })
                        total[_('Worked Hours')] += worked_hours
                        total[_('Duty Hours')] += dh
                        total[_('Running')] += diff
                        total[_('Difference')] = work_current_month_diff
                    else:
                        res['hours'].append({
                            'name': date_line.strftime(date_format),
                            'running': sign_float_time_convert(current_month_diff),
                            'dh': sign_float_time_convert(dh),
                            'worked_hours': sign_float_time_convert(worked_hours),
                            'diff': sign_float_time_convert(diff),
                        })
                        total['worked_hours'] += worked_hours
                        total['duty_hours'] += dh
                        total['work_current_month_diff'] = work_current_month_diff
                        total['diff'] += diff
                    res['total'] = total
                return res

    def write(self, vals):
        if 'state' in vals and vals['state'] == 'done':
            for sheet in self:
                vals['total_diff_hours'] = sheet.calculate_diff_hours
                vals['total_duty_hours_done'] = sheet.total_duty_hours
        elif 'state' in vals and vals['state'] == 'draft':
            for sheet in self:
                vals['total_diff_hours'] = 0.0
                vals['total_duty_hours_done'] = sheet.total_duty_hours
        return super(Sheet, self).write(vals)

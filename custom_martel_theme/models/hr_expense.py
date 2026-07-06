# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        compute='_compute_analytic_account_id',
        inverse='_inverse_analytic_account_id',
        store=True,
    )

    @api.depends('analytic_distribution')
    def _compute_analytic_account_id(self):
        for expense in self:
            distribution = expense.analytic_distribution or {}
            if distribution:
                # A distribution key may hold several comma-separated account ids
                # (one per analytic plan): keep the first one, matching the
                # single-account UI we expose on the expense form.
                first_key = next(iter(distribution))
                account_id = int(str(first_key).split(',')[0])
                expense.analytic_account_id = self.env['account.analytic.account'].browse(account_id)
            else:
                expense.analytic_account_id = False

    def _inverse_analytic_account_id(self):
        for expense in self:
            if expense.analytic_account_id:
                expense.analytic_distribution = {str(expense.analytic_account_id.id): 100}
            else:
                expense.analytic_distribution = {}


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    # Plain integer mirror of the record id: the "Report ID" list column
    # uses it so XLSX exports show the number instead of the external id
    # ("__export__.hr_expense_sheet_...") that exporting `id` produces.
    # No @api.depends on purpose: the id never changes, so the value is
    # computed once at create (and backfilled on module upgrade).
    report_ref = fields.Integer(
        string='Report ID',
        compute='_compute_report_ref',
        store=True,
    )

    def _compute_report_ref(self):
        for sheet in self:
            sheet.report_ref = sheet.id

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

    # Plain text mirror of the analytic account name, used as the "Analytic
    # Account" column of the expense lists. A many2one column would export its
    # display_name ("Internal NL - Martel Innovate BV"); this exports the bare
    # project name. Not stored: it is read-only display/export data, so there is
    # nothing to search or group on that analytic_account_id does not cover.
    analytic_account_name = fields.Char(
        string='Analytic Account',
        related='analytic_account_id.name',
    )

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
    # Filled explicitly at create: a stored computed field would need a
    # dependency to be recomputed, and `id` is not a field one can depend on.
    report_ref = fields.Integer(
        string='Report ID',
        readonly=True,
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        sheets = super().create(vals_list)
        for sheet in sheets:
            sheet.report_ref = sheet.id
        return sheets

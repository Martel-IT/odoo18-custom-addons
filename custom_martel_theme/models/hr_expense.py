# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        compute='_compute_analytic_account_id',
        inverse='_inverse_analytic_account_id',
        store=False,
    )

    @api.depends('analytic_distribution')
    def _compute_analytic_account_id(self):
        for expense in self:
            distribution = expense.analytic_distribution or {}
            if distribution:
                # Prende il primo (e unico) account dalla distribuzione
                account_id = int(next(iter(distribution)))
                expense.analytic_account_id = self.env['account.analytic.account'].browse(account_id)
            else:
                expense.analytic_account_id = False

    def _inverse_analytic_account_id(self):
        for expense in self:
            if expense.analytic_account_id:
                expense.analytic_distribution = {str(expense.analytic_account_id.id): 100}
            else:
                expense.analytic_distribution = {}

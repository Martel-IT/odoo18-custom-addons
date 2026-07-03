from odoo import api, fields, models


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def _message_set_main_attachment_id(self, attachments, force=False, filter_xml=True):
        """Reject unsupported attachments (e.g. HEIC) posted on the report.

        Same chokepoint protection as hr.expense: avoids the core crash on a
        False mimetype and keeps only PDF/standard images on expense reports.
        """
        self.env['ir.attachment']._assert_expense_attachments_allowed(attachments)
        return super()._message_set_main_attachment_id(
            attachments, force=force, filter_xml=filter_xml)

    date_approve = fields.Date(
        string='Approval Date',
        compute='_compute_date_approve',
        # store=False → no DB column, works immediately without module upgrade
    )

    @api.depends('state', 'message_ids.tracking_value_ids')
    def _compute_date_approve(self):
        """
        Read the approval date from the chatter: find the first tracking message
        where the 'state' field was set to 'approve' (label contains 'approv').
        Falls back to False if no such message exists.
        """
        for sheet in self:
            approval_date = False
            if sheet.state in ('approve', 'post', 'done'):
                # tracking_value_ids is restricted to base.group_system in
                # Odoo 18: read via sudo so non-admin users (e.g. secretariat
                # printing the report) don't hit an AccessError.
                for msg in sheet.sudo().message_ids.sorted('date'):
                    for tv in msg.tracking_value_ids:
                        field_name = tv.field_id.name if tv.field_id else ''
                        new_val = (tv.new_value_char or '').lower()
                        if field_name == 'state' and 'approv' in new_val:
                            approval_date = msg.date.date()
                            break
                    if approval_date:
                        break
            sheet.date_approve = approval_date

    def action_print_expense_report(self):
        """Print the expense sheet report PDF only. Attachments are NOT
        merged in anymore: they have their own dedicated button
        (action_download_attachments_pdf). The download filename comes from
        the report action's print_report_name."""
        self.ensure_one()
        return self.env.ref(
            'custom_download_attachments.action_report_expense_sheet_martel'
        ).report_action(self)

    def action_download_attachments_pdf(self):
        """Download all expense attachments merged into a single PDF."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/download/expense_attachments?active_ids={self.id}',
            'target': 'new',
        }

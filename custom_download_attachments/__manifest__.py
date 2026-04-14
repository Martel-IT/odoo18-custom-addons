{
    'name': 'Expense Attachments Downloader',
    'author': 'Martel Innovate IT',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Download all expense report attachments as single PDF',
    'depends': ['base', 'hr_expense'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/download_attachments.xml',
        'views/report_expense_sheet.xml',
        'views/hr_expense_sheet_view.xml',
    ],
    'installable': True,
    'application': False,
}

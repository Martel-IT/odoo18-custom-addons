# -*- coding: utf-8 -*-
{
    'name': "HR Holidays Hours/8 Rule",
    'author': "Martel Innovate",
    'version': "18.0.1.0.0",
    'summary': "Force Time Off days computation as hours / 8.0, bypassing resource_calendar logic.",
    'description': """
Customization of hr_holidays for Odoo 18: enforces the business rule
`days = number_of_hours / 8.0` everywhere leave duration is computed,
so part-time and flexible-schedule employees are billed days consistent
with the 8h = 1 day contractual mapping instead of each employee's
resource_calendar_id / working-hours logic.
""",
    'website': "http://www.martel-innovate.com",
    'category': 'Human Resources',
    'depends': ['hr_holidays'],
    'installable': True,
    'application': False,
    'data': [],
}

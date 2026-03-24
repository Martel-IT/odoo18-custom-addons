# -*- coding: utf-8 -*-
{
    'name': 'Martel Custom Theme',
    'version': '18.0.1.0.0',
    'summary': 'Custom UI theme for Martel Innovate – branded colors, full-width timesheet grid, weekend highlighting, chatter at bottom.',
    'author': 'Martel Innovate',
    'website': 'https://www.martel-innovate.com',
    'category': 'Themes/Backend',
    'license': 'LGPL-3',
    'depends': [
        'web',
        'mail',
        'hr_timesheet',
    ],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'custom_martel_theme/static/src/scss/custom_theme.scss',
            'custom_martel_theme/static/src/js/weekend_highlighter.js',
            'custom_martel_theme/static/src/js/sidebar_logo.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}

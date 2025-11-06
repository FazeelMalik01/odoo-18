
{
    'name': "zkteco_attendance",
    'summary': "Integrate ZKTeco MB360 with Odoo HR Attendance",
    'description': "This module fetches attendance logs from the ZKTeco MB360 biometric device and updates Odoo HR Attendance automatically.",
    'author': "Muhammad Faizan",
    'website': "https://www.techcogg.com",
    'category': 'Human Resources',
    'version': '2.0',
    'depends': ['hr_attendance','hr'],
    'license': 'LGPL-3',

    'data': [
        'security/ir.model.access.csv', 
        'views/zkteco_attendance_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
  
  
}


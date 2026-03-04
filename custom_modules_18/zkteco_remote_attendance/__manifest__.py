{
    'name': "ZKTeco Remote Attendance",
    'summary': "Allow employees to mark attendance remotely based on location coordinates",
    'author': "Fazeel Malik",
    'website': "https://www.yourwebsite.com",
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['web','hr_attendance', 'portal', 'hr'],
    'license': 'LGPL-3',
    'data': [
        'views/employee_view.xml',
        'security/ir.model.access.csv',
        'views/assets.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'zkteco_remote_attendance/static/src/js/portal_attendance.js',
        ],
    },
    'installable': True,
    
}



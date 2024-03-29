#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_scrcpy.settings')
try:
    os.remove('db.sqlite3')
except Exception as e:
    pass
try:
    from django.core.management import execute_from_command_line
except ImportError as exc:
    raise ImportError(
        "Couldn't import Django. Are you sure it's installed and "
        "available on your PYTHONPATH environment variable? Did you "
        "forget to activate a virtual environment?"
    ) from exc
execute_from_command_line(['manage.py', 'migrate'])
execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
print('\n==================================================')
print('Please create a super user !!!')
print('==================================================')
execute_from_command_line(['manage.py', 'createsuperuser'])

#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_scrcpy.settings')

# 1.清空数据库
if input("(1).是否清除旧数据库：1是，0否 ___ ") == '1':
    try:
        os.remove('db.sqlite3')
        print("成功清除旧数据库信息")
    except Exception as e:
        pass
print()
try:
    from django.core.management import execute_from_command_line
except ImportError as exc:
    raise ImportError(
        "Couldn't import Django. Are you sure it's installed and "
        "available on your PYTHONPATH environment variable? Did you "
        "forget to activate a virtual environment?"
    ) from exc

# 2.更新数据库结构和静态文件
print("(2).更新数据库结构和静态文件")
execute_from_command_line(['manage.py', 'migrate'])
execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
print("更新成功")
print()

# 3.创建超级用户
if input("(3).是否创建超级用户：1是，0否 ___ ") == '1':
    print('\n==================================================')
    print('Please create a super user !!!')
    print('==================================================')
    execute_from_command_line(['manage.py', 'createsuperuser'])
    print("创建成功")

#!/usr/bin/env python
"""
Django ka command-line utility file.
Isi file se saare commands chalate hain jaise:
  python manage.py runserver
  python manage.py migrate
  python manage.py createsuperuser
"""
import os
import sys


def main():
    # Settings file set karo
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VG.settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django import nahi ho raha. "
            "Kya virtual environment activate ki hai? "
            "Aur kya 'pip install django' kiya hai?"
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

"""
WSGI config for credit_approval_system project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'credit_approval_system.settings')

application = get_wsgi_application()
#!/bin/bash
set -e

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Loading demo data (if no users exist)..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.exists():
    import subprocess
    subprocess.call(['python', 'manage.py', 'load_demo'])
    print('Demo data loaded!')
else:
    print('Data already exists, skipping demo load.')
"

echo "==> Starting gunicorn..."
gunicorn finpro.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
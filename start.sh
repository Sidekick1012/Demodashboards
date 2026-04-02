#!/bin/bash
python manage.py migrate --no-input
python manage.py collectstatic --no-input
python manage.py load_demo
gunicorn finpro.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 120

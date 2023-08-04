source venv/bin/activate
nohup gunicorn store_management.wsgi:application -b :8000 &

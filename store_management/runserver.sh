cd  /home/parentenv/bin/ && source activate && cd /home/birika_projects/Jensen-Stores/store_management
nohup gunicorn store_management.wsgi:application -b :8000 &

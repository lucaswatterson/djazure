#!/bin/bash

python manage.py createsuperuser \
    --username=$DJANGO_SUPERUSER_USER \
    --email=$DJANGO_SUPERUSER_USER@example.com \
    --noinput \
    2>/dev/null

if [ $? -eq 0 ]; then
    echo "Superuser was created successfully"
else
    echo "Superuser was not created."
fi

#!/bin/sh

# Wait for postgres to be ready
echo "Waiting for postgres..."
while ! python -c "import psycopg2; psycopg2.connect(host='$ECL_DB_HOST', port='$ECL_DB_PORT', user='$ECL_DB_USER', password='$ECL_DB_PASSWORD', dbname='$ECL_DB_NAME')" 2>/dev/null; do
    sleep 1
done
echo "PostgreSQL is ready!"

if [ "$RUN_WORKER" = "True" ]; then
    exec celery -A pecl.celery worker --loglevel=info -E
else
    if [ "$RUN_MIGRATIONS" = "True" ]; then
        python manage.py migrate

        python manage.py ensuresuperuser --email=$ECL_ADMIN_EMAIL --password=$ECL_ADMIN_PASSWORD
        python manage.py verifyagents
        python manage.py verifysources
    fi

    exec python manage.py runserver 0.0.0.0:$PORT
fi

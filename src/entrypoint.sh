#!/bin/sh
# Commands run in the docker container before starting up the application.

if [ "$DJANGO_CONFIG" = "prod" ]
then
    # Make sure our upload directory has correct ownership and is writable.
    chown app:app /app/uploads
    chmod ug+rwX /app/uploads

    # Wait for Postgres to be ready before attempting to apply migrations
    echo "Waiting for postgres..."
    while ! nc -z ${DJANGO_DB_HOST:=127.0.0.1} ${DJANGO_DB_PORT:=5432}; do
      sleep 1
    done
    echo "PostgreSQL found"
fi

echo "Applying any pending migrations..."
gosu app:app python manage.py migrate

echo "Loading database fixtures..."
gosu app:app python manage.py loaddata preferencesets subjects tiptypes

echo "Loading default content..."
gosu app:app python manage.py importdir /content

# The below does not actually work since createsuperuser command does not allow password to be
# specified on the command line. Need to write a custom admin command or do this as a Migration.
# See https://stackoverflow.com/questions/6244382/how-to-automate-createsuperuser-on-django
#if [ ! -z "$DJANGO_ADMIN_USER" ] && [ ! -z "$DJANGO_ADMIN_PASSWORD" ]; then
#  echo "Creating superuser" $DJANGO_ADMIN_USER
#  python manage.py createsuperuser --username $DJANGO_ADMIN_USER --password $DJANGO_ADMIN_PASSWORD
#fi

exec gosu app:app "$@"

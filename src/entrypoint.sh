#!/bin/sh
# Commands run in the docker container before starting up the application.

# Wait for Postgres to be ready before attempting to apply migrations

if [ "$DJANGO_CONFIG" = "prod" ]
then
    echo "Waiting for postgres..."

    while ! nc -z ${DJANGO_DB_HOST:=127.0.0.1} ${DJANGO_DB_PORT:=5432}; do
      sleep 1
    done

    echo "PostgreSQL found"
fi


echo "Applying any pending migrations..."
python manage.py migrate

echo "Loading preference sets"
python manage.py loaddata preferencesets

echo "Loading default content"
python manage.py importdir /content

# The below does not actually work since createsuperuser command does not allow password to be
# specified on the command line. Need to write a custom admin command or do this as a Migration.
# See https://stackoverflow.com/questions/6244382/how-to-automate-createsuperuser-on-django
#if [ ! -z "$DJANGO_ADMIN_USER" ] && [ ! -z "$DJANGO_ADMIN_PASSWORD" ]; then
#  echo "Creating superuser" $DJANGO_ADMIN_USER
#  python manage.py createsuperuser --username $DJANGO_ADMIN_USER --password $DJANGO_ADMIN_PASSWORD
#fi

exec "$@"

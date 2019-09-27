# Simple docker build that assumes the application has already been built in the local directory.
# Prerequisites:
#   npm install
#   grunt build
# Then:
#   docker build . -t clusive
#   docker run -p 8000:8000 -e DJANGO_CONFIG=local clusive

FROM python:3.7-alpine as base

# No point caching bytecode for single run
ENV PYTHONDONTWRITEBYTECODE 1

# Don't buffer log output inside the container
ENV PYTHONUNBUFFERED 1

COPY requirements.txt /
RUN \
  apk add --no-cache postgresql-libs git gcc musl-dev postgresql-dev npm && \
  python -m pip install -r /requirements.txt --no-cache-dir

# Don't run as root
RUN mkdir -p /app /home/app
RUN addgroup -S app && adduser -S -G app app && chown app /app /home/app
USER app

WORKDIR /app

COPY . .

RUN python manage.py collectstatic --no-input

EXPOSE 8000
STOPSIGNAL SIGINT

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "clusive_project.wsgi", "--bind=0.0.0.0:8000"]

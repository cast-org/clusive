# Build docker image for the Clusive app
# This does a full clean build, including npm install, grunt build and downloading the NLTK data
# Uses a two-stage build process to make the final package smaller, since it does not include all the build tools.
#
# Basic usage:
#
#   docker build . -t clusive
#   docker run -p 8000:8000 -e DJANGO_CONFIG=local --name clusive clusive
#   docker exec -it clusive python manage.py createsuperuser
#   Log in to http://localhost:8000/admin as the superuser and "Rescan Books"

###
### The builder image (first of two stages)
###

FROM python:3.7-alpine as base

COPY requirements.txt /
RUN \
  apk add --no-cache postgresql-libs git gcc musl-dev postgresql-dev npm && \
  python -m pip wheel -r /requirements.txt --no-cache-dir --no-deps --wheel-dir /wheels

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN ./node_modules/grunt-cli/bin/grunt build

# Build is complete. Clean up items in /app that are not needed to run the live site.
RUN rm -rf node_modules Grunt* package*

###
### Construct the slim image for deployment (second stage)
###

FROM python:3.7-alpine

RUN apk add --no-cache postgresql-libs

# No point caching bytecode for single run
ENV PYTHONDONTWRITEBYTECODE 1

# Don't buffer log output inside the container
ENV PYTHONUNBUFFERED 1

COPY --from=base /wheels /wheels
RUN pip install --no-cache /wheels/*

# Don't run as root
RUN mkdir -p /app /home/app
RUN addgroup -S app && adduser -S -G app app
RUN chown -R app:app /app
USER app

WORKDIR /app

RUN python -m nltk.downloader wordnet

COPY --from=base /app /app

RUN python manage.py collectstatic --no-input

EXPOSE 8000
STOPSIGNAL SIGINT

ENTRYPOINT ["/app/entrypoint.sh"]

HEALTHCHECK --interval=10s --timeout=3s \
	CMD wget --quiet --tries=1 --spider http://localhost:8000/ || exit 1

# gunicorn configuration suggestions from https://pythonspeed.com/articles/gunicorn-in-docker/
CMD ["gunicorn", "clusive_project.wsgi", "--bind=0.0.0.0:8000", "--worker-tmp-dir=/dev/shm", \
	"--workers=2", "--threads=4", "--worker-class=gthread"]

# Build docker image for the Clusive app
# This does a full clean build, including npm install, grunt build and downloading the NLTK data
# Uses a two-stage build process to make the final package smaller, since it does not include all the build tools.
#
# Basic usage:
#
#   docker build . -t clusive
#   docker run -p 8000:8000 -e DJANGO_CONFIG=local --name clusive clusive
#   docker exec -it clusive python manage.py createsuperuser
#   Log in to http://localhost:8000/admin as the superuser

###
### The builder image (first of two stages)
###

FROM python:3.9-slim-bullseye as base

# OS repositories only have node 12; we want 16.  Use nodesource script to add newer repo.
RUN apt-get update && \
  apt-get -y install curl

RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash -

RUN apt-get -y install --no-install-recommends bzip2 g++ gcc git libpq5 libpq-dev nodejs python3-dev && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

COPY requirements.txt /
RUN python -m pip wheel -r /requirements.txt --no-cache-dir --no-deps --wheel-dir /wheels

# Download this in builder so that it's more likely cached; data doesn't change often.
# Outputs a warning message when it runs.
RUN python -m pip install nltk
RUN python -m nltk.downloader -d /usr/local/share/nltk_data wordnet &&  \
    python -m nltk.downloader -d /usr/local/share/nltk_data omw-1.4 && \
    python -m nltk.downloader -d /usr/local/share/nltk_data averaged_perceptron_tagger

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

FROM python:3.9-slim-bullseye

RUN apt-get update && \
  apt-get -y install --no-install-recommends libpq5 netcat-traditional wget gosu pandoc && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# No point caching bytecode for single run
ENV PYTHONDONTWRITEBYTECODE 1

# Don't buffer log output inside the container
ENV PYTHONUNBUFFERED 1

COPY --from=base /wheels /wheels
RUN pip install --no-cache /wheels/*

COPY --from=base /usr/local/share/nltk_data /usr/local/share/nltk_data

# Don't run as root
RUN addgroup --system app && adduser --system --ingroup app app
RUN mkdir -p /app /content /resources
RUN chown -R app:app /app /content /resources

WORKDIR /app

COPY --from=base /app/target /app
COPY src/entrypoint.sh /app

COPY content /content
COPY resources /resources

RUN gosu app:app python manage.py collectstatic --no-input

EXPOSE 8000
STOPSIGNAL SIGINT

ENTRYPOINT ["/app/entrypoint.sh"]

HEALTHCHECK --interval=10s --timeout=3s --start-period=120s \
	CMD wget --quiet --tries=1 --spider http://localhost:8000/ || exit 1

# gunicorn configuration suggestions from https://pythonspeed.com/articles/gunicorn-in-docker/
CMD ["gunicorn", "clusive_project.wsgi", "--bind=0.0.0.0:8000", "--worker-tmp-dir=/dev/shm", \
	"--workers=2", "--threads=4", "--worker-class=gthread"]

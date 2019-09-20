# Build docker image
#   After 'npm run build':
#   docker build . -t dockerreg.cast.org/corgi:latest -t dockerreg.cast.org/corgi:`git rev-parse HEAD` -t us.gcr.io/acoustic-art-180717/corgi:`git rev-parse HEAD`
#   docker run -p 3000:80 -e APP_CONFIG=qa dockerreg.cast.org/corgi

### This is a multi-stage build

###
### The builder image
###

FROM python:3.7-alpine as base

COPY requirements.txt /
RUN \
  apk add --no-cache postgresql-libs git gcc musl-dev postgresql-dev npm && \
  python -m pip wheel -r /requirements.txt --no-cache-dir --no-deps --wheel-dir /wheels

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN ./node_modules/grunt-cli/bin/grunt build

# Build is complete. Clean up items in /app that are not needed to run the live site.
RUN rm -rf node_modules Grunt* package*

###
### The image for deployment
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
RUN mkdir -p /home/app
RUN addgroup -S app && adduser -S -G app app

WORKDIR /app

COPY --from=base /app /app
RUN chown -R app:app /app

USER app

RUN python manage.py collectstatic --no-input

EXPOSE 8000
STOPSIGNAL SIGINT
ENTRYPOINT ["python", "manage.py"]
CMD ["runserver", "0.0.0.0:8000"]

#COPY docker/configurations /usr/share/configurations
#ADD  docker/entrypoint.sh /usr/local/bin/

#ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
#CMD ["nginx", "-g", "daemon off;"]

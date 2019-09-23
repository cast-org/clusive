# Clusive Django Web Application

This repository contains the [Django-based](https://www.djangoproject.com/) "fall pilots" web application for the CISL project, Clusive.

## Quick Links for Further Reading

* [Django's documentation](https://docs.djangoproject.com/en/2.2/)
  * [Customizing authentication in Django](https://docs.djangoproject.com/en/2.2/topics/auth/customizing/), a specific need of the project

## Setting up the Development Environment

### Prerequisites

* [Python 3](https://www.python.org/downloads/) 
  * On Mac, Homebrew is the easiest way to do this (OS X comes with Python 2.7); you'll need to use the *python3* and *pip3* commands to distinguish Python 2 and Python 3, or change your aliases
* [virtualenv](https://virtualenv.pypa.io/en/stable/installation/) (strongly recommended for maintaining an isolated environment and dependencies)
* [Postgres](https://www.postgresql.org/) may be necessary for the psycopg2 dependency (Homebrew on OS X can take care of this)
* [npm](https://www.npmjs.com/), as the front-end dependencies are managed with it

### Create and activitate virtualenv for the project

* Create: `virtualenv ENV`
* Activate: 
  - Windows: `.\ENV\Scripts\activate`
  - Mac/Linux: `source ENV/bin/activate`

You'll need to activate the environment each time you're working on the project in order to continue using the isolated environment.

### Build front-end Javascript dependencies

* `npm install`
* `grunt build`

#### Notes on front-end dependencies generally

* Front-end JS libraries are combined with Webpack and end up in `shared\static\shared\js\lib\main.js`
* Front-end assets for infusion and figuration (CSS, etc) are copied to `shared\static\shared\js\lib\` in their own directories
* The Django template at `shared\templates\shared\base.html` sets a Javascript global called `DJANGO_STATIC_ROOT` for the use of client-side Javascript needing to construct references to static content

#### Notes on Readium dependencies

Until the `@dita/reader` repo is made public, you'll need to do the following to have the Readium code properly integrated and building:

**Note**: This needs to be done after every run of `npm install`, because the install delinks any linked packages (see https://github.com/npm/npm/issues/17287)

1. Check out a local copy of ` https://github.com/d-i-t-a/R2D2BC.git`, install / build it, and run `npm link` in that repo's directory
2. Run `npm link @dita/reader` in this repo's directory

The above process creates a package link between this project's `node_modules` directory (in `@dita/reader`) and the local directory containing the reader code, so it can be pulled in by the build scripts

### Install Python Dependencies 

* `pip install -r requirements.txt`

### Do the Initial Database Migrations

The current configuration (for development) uses sqlite3, so no database setup is required.

* `python manage.py migrate`

### Create a superuser
* `python manage.py createsuperuser`

### Basic Verification

* Launch the server: `python manage.py runserver`
* Confirm you see the Django success page at `http://localhost:8000`
* Confirm the superuser can log in at `http://localhost:8000/admin/` 

## Running under Docker

Build:
 
`docker build . -t clusive`

Run for local development (creates an empty sqlite database at each run):

`docker run -e DJANGO_CONFIG=local -p 8000:8000 clusive` 

Run with production settings and Postgres database:

```
docker run -p 8000:8000 \\
  -e DJANGO_CONFIG=prod -e DJANGO_SECRET_KEY=<key>  \\
  -e DJANGO_DB_HOST=<host> -e DJANGO_DB_NAME=<name> \\
  -e DJANGO_DB_USER=<user> -e DJANGO_DB_PASSWORD=<password> \\
  clusive
```


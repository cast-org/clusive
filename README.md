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

#### Notes

* Front-end JS libraries are combined with Webpack and end up in `shared\static\shared\js\lib\main.js`
* Front-end assets for infusion and figuration (CSS, etc) are copied to `shared\static\shared\js\lib\` in their own directories
* The Django template at `shared\templates\shared\base.html` sets a Javascript global called `DJANGO_STATIC_ROOT` for the use of client-side Javascript needing to construct references to static content

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

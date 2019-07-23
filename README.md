# Clusive Django Web Application

This repository contains the [Django-based](https://www.djangoproject.com/) "fall pilots" web application for the CISL project, Clusive.

## Setting up the Development Environment

### Prerequisites

* [Python 3](https://www.python.org/downloads/)
* [virtualenv](https://virtualenv.pypa.io/en/stable/installation/) (strongly recommended for maintaining an isolated environment and dependencies)

### Create and activitate virtualenv for the project

* Create: `virtualenv ENV`
* Activate: 
  - Windows: `.\ENV\Scripts\activate`
  - Mac/Linux: `source ENV\Scripts\activate`

You'll need to activate the environment each time you're working on the project in order to continue using the isolated environment.

### Install Python Dependencies 

* `pip install -r requirements.txt`

### Do the Initial Database Migrations

The current configuration (for initial development) uses sqlite3, so no database setup is required.

* `python manage.py migrate`

### Create a superuser
* `python manage.py createsuperuser`
* Confirm the superuser can log in via `http://localhost:8000/admin/` (after launching server)

## Common Operations

* Launch the server: `python manage.py runserver`
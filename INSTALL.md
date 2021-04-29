# Installation of Clusive

Clusive can be installed in several ways, either as a standalone server
or a Docker container. 
To try it out quickly using Docker skip ahead to that section.

## Local Installation

Note: all steps between **Create/Activitate Virtual Environment** and **Create a Superuser** can be run using `local_install.sh` (on Unix-based systems) or `local_install.ps1` (on Windows) to more easily set up or refresh a local environment. Be sure to set up your virtual environment first.

### Prerequisites

* [Python 3](https://www.python.org/downloads/)
  * Version 3.7.4 or later, but less than 3.9. On Mac, Homebrew is the easiest way to install.
  * Note: Version 3.9 removes member `tp_print` from `PyTypeObject` which is
    used by some of Clusive's dependencies; see "[What’s New In Python 3.9](https://docs.python.org/3.9/whatsnew/3.9.html#id3)".
* [virtualenv](https://virtualenv.pypa.io/en/latest/) 
  * Not required, but highly recommended for maintaining an isolated environment and dependencies.
* [Postgres](https://www.postgresql.org/) 
  * Version 11.5 or later. Used in the deployment configuration.
* [Node.js](https://nodejs.org/)
  * Not required to run the Clusive server, but for development it is needed 
    since we use:
    * [npm](https://www.npmjs.com/get-npm) - Package manager
    * [Grunt](https://gruntjs.com/) - Task runner

  
### Clone the Clusive Repository

Clone the Clusive repository to your local machine and check out the appropriate branch. Note that there are currently no released versions.
* [master branch](https://github.com/cast-org/clusive/) - the most stable version
* [development branch](https://github.com/cast-org/clusive/tree/development) - the latest code changes
 

### Create/Activitate Virtual Environment
Always activate and use the python virtual environment to maintain an 
isolated environment for Clusive's dependencies.

* [Create the virtual environment](https://docs.python.org/3/library/venv.html)
  (one time setup): 
  - `python -m venv ENV` 
  - Or do this via your IDE, e.g. [Intellij's support for virtualenv](https://www.jetbrains.com/help/idea/creating-virtual-environment.html)

* Activate (every command-line session):
  - Windows: `.\ENV\Scripts\activate`
  - Mac/Linux: `source ENV/bin/activate`


### Build Front-end Javascript Dependencies

Run in the Clusive directory:
* `npm install`
* `grunt build`
  - Use the noclean option to preserve data on subsequent builds: \
  `grunt build-noclean`
This creates the compiled, runnable server in the Clusive/target directory.

#### Front-end Dependency Notes

* Front-end JS libraries are combined with Webpack and end up in `shared\static\shared\js\lib\main.js`
* Front-end assets for Infusion and Figuration (CSS, etc) are copied to `shared\static\shared\js\lib\` in their own directories
* The Django template at `shared\templates\shared\base.html` sets a Javascript global called `DJANGO_STATIC_ROOT` for the use of client-side Javascript needing to construct references to static content

### Install Python Dependencies

Run in the Clusive directory:
* `pip install -r requirements.txt`
* If necessary, refer to these possible solutions for [psycopg2 library issues](https://stackoverflow.com/questions/26288042/error-installing-psycopg2-library-not-found-for-lssl) on Mac

### Download WordNet Data

Run in the Clusive directory:
* `python -m nltk.downloader wordnet`
* possible solutions for [certificate issues](https://stackoverflow.com/questions/38916452/nltk-download-ssl-certificate-verify-failed) on Mac

### Initialize Local Database

The local development configuration uses sqlite, so no database setup is required.

To initialize the schema and initial data, run in the Clusive\target directory:
* `python manage.py migrate`
* `python manage.py loaddata preferencesets tiptypes subjects` 

### Import public content
There are a number of learning materials ready for import in the Clusive\content directory.

For each one that you want to make available, run a command like this in 
the Clusive\target directory:
* `python manage.py import ..\content\cast-lexington\*`

You can also import the entire `content` directory in one go:
* `python manage.py importdir ..\content`

The `import` command can be used to import a single EPUB file, 
or multiple files which are considered to be a set of leveled versions 
of the same content. A glossary JSON file and directory of images that
it refers to can also be included on the command line.
The content directory contains many examples of these.  

### Create a Superuser

Run in the Clusive\target directory:
* `python manage.py createsuperuser`

### Verify the Application

Run in the Clusive\target directory:
* `python manage.py runserver`
* Verify Clusive login page: http://localhost:8000
* Verify Clusive admin site with the superuser login: http://localhost:8000/admin/

### Local Development

* `grunt watch:devRebuild` can be used to watch the `src` directory and run the build to `target` again on changes, reducing the need to manually run the build while working locally

## Docker Production Installation

In the Clusive directory, build the Docker image:

`docker build . -t clusive`

Or, in the command lines below, you can use the pre-built `castudl/clusive` image from Docker Hub.

Run with local development settings (creates an empty sqlite database at each run):

`docker run -e DJANGO_CONFIG=local -p 8000:8000 clusive`

Run with production settings and Postgres database 
(_note:_ the production settings require HTTPS):

```
docker run -p 8000:8000 \\
  -e DJANGO_CONFIG=prod -e DJANGO_SECRET_KEY=<key>  \\
  -e DJANGO_DB_HOST=<host> -e DJANGO_DB_NAME=<name> \\
  -e DJANGO_DB_USER=<user> -e DJANGO_DB_PASSWORD=<password> \\
  clusive
```
Docker will run any pending database migrations and import the default books at startup, but users must be added manually:

* `docker exec -it <container_id> python manage.py createsuperuser`

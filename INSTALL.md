# Installation of Clusive

Clusive can be installed locally for development or for production use via Docker.


## Local Installation

### Prerequisites

* [Python 3](https://www.python.org/downloads/)
  * Version 3.7.4 or later. On Mac, Homebrew is the easiest way to install
* [virtualenv](https://virtualenv.pypa.io/en/latest/) 
  * Highly recommended for maintaining an isolated environment and dependencies
* [Postgres](https://www.postgresql.org/) 
  * Version 11.5 or later. Used in the deployment configuration 
* [Node.js](https://nodejs.org/)
  * Used for the build system and to manage all other dependencies using:
    * [npm](https://www.npmjs.com/get-npm) - Package manager
    * [Grunt](https://gruntjs.com/) - Task runner

  
### Clone the Clusive Repository

Clone the Clusive repository to your local machine and check out the appropriate branch. Note that there are currently no released versions.
* [master branch](https://github.com/cast-org/clusive/) - the most stable version
* [development branch](https://github.com/cast-org/clusive/tree/development) - the latest code changes
 

### Create/Activitate Virtual Environment
Always activate and use the virtual environment to maintain an isolated environment.

* [Create the virtual environment](https://docs.python.org/3/library/venv.html): 
  - `python -m venv ENV` 
  - If applicable [Intellij's support for virtualenv](https://www.jetbrains.com/help/idea/creating-virtual-environment.html)

* Activate:
  - Windows: `.\ENV\Scripts\activate`
  - Mac/Linux: `source ENV/bin/activate`


### Build Front-end Javascript Dependencies

Run in the Clusive directory:
* `npm install`
* `grunt build`
  - Use the noclean option to preserve data on subsequent builds: `grunt build -noclean`
 

#### Front-end Dependency Notes

* Front-end JS libraries are combined with Webpack and end up in `shared\static\shared\js\lib\main.js`
* Front-end assets for Infusion and Figuration (CSS, etc) are copied to `shared\static\shared\js\lib\` in their own directories
* The Django template at `shared\templates\shared\base.html` sets a Javascript global called `DJANGO_STATIC_ROOT` for the use of client-side Javascript needing to construct references to static content

### Install Python Dependencies

Run in the Clusive directory:
* `pip install -r requirements.txt`
* possible solutions for [psycopg2 library issues](https://stackoverflow.com/questions/26288042/error-installing-psycopg2-library-not-found-for-lssl) on Mac

### Download WordNet Data

Run in the Clusive directory:
* `python -m nltk.downloader wordnet`
* possible solutions for [certificate issues](https://stackoverflow.com/questions/38916452/nltk-download-ssl-certificate-verify-failed) on Mac

### Initialize Local Database

The local development configuration uses sqlite3, so no database setup is required.

Run in the /target directory:
* `python manage.py migrate`

### Create a Superuser

Run in the /target directory:
* `python manage.py createsuperuser`

### Verify the Application

Run in the /target directory:
* Launch the server `python manage.py runserver` from the target directory
* Verify Clusive Learning Environment login page `http://localhost:8000`
* Verify Clusive Admin site with the superuser login `http://localhost:8000/admin/`

### Import Default Content

In the Clusive Admin site, navigate to "Books" and click "Rescan Books" to load the default content.

### Import Custom Content

To add additional content, each EPUB must be unpacked, a manifest generated, and the files manually 
made part of the application's static files:
* Clone and install [r2-shared-js](https://github.com/readium/r2-shared-js) from Github
* Unpack EPUBs in the r2-shared-js directory
  * `npm run cli file.epub output-dir`
* Copy unpacked EPUB directory in output-dir to `/shared/static/shared/pubs/short-name-for-new-pub`
* Build and restart the application
* In the Clusive Admin site, navigate to "Books" and click "Rescan Books"


## Docker Production Installation

In the Clusive directory, build the Docker image:

`docker build . -t clusive`

Run with local development settings (creates an empty sqlite database at each run):

`docker run -e DJANGO_CONFIG=local -p 8000:8000 clusive`

Run with production settings and Postgres database:

```
docker run -p 8000:8000 \\
  -e DJANGO_CONFIG=prod -e DJANGO_SECRET_KEY=<key>  \\
  -e DJANGO_DB_HOST=<host> -e DJANGO_DB_NAME=<name> \\
  -e DJANGO_DB_USER=<user> -e DJANGO_DB_PASSWORD=<password> \\
  clusive
```
Docker will run any pending database migrations. Users and books are added manually:

* `docker exec -it <container_id> python manage.py createsuperuser`
* In the Clusive Admin site, navigate to "Books" and click "Rescan Books"

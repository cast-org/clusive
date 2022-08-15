# Installation of Clusive

Clusive can be installed in several ways, either as a standalone server
or a Docker container. 
To try it out quickly using Docker skip ahead to that section.

## Local Installation

Note: all steps between **Create/Activitate Virtual Environment** and **Create a Superuser** can be run using `local_install.sh` (on Unix-based systems) or `local_install.ps1` (on Windows) to more easily set up or refresh a local environment. Be sure to set up your virtual environment first.

### Prerequisites

* [Python 3](https://www.python.org/downloads/)
  * Version 3.7.4 up to 3.9. (3.10+ not tested yet). On Mac, Homebrew is the easiest way to install.
* [Django 3]
  * Version 3.2.14+, installed with other Python dependencies as documented in
    section [Install Python Dependencies](#install-python-dependencies).
* [virtualenv](https://virtualenv.pypa.io/en/latest/) 
  * Not required, but highly recommended for maintaining an isolated environment and dependencies.
* [Postgres](https://www.postgresql.org/) 
  * Version 11.5 or later. Used in the deployment configuration.
* [Node.js](https://nodejs.org/)
  * Version 16 or later. Not required to run the Clusive server, but for development it is needed. 
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
* For instance, as suggested in the answers on that page, you might need to use:
  * `LDFLAGS="-L/usr/local/opt/openssl/lib" pip install -r requirements.txt`

### Download WordNet Data

Run in the Clusive directory:
* `python -m nltk.downloader wordnet`
* possible solutions for [certificate issues](https://stackoverflow.com/questions/38916452/nltk-download-ssl-certificate-verify-failed) on Mac

### Initialize Local Database

The local development configuration uses sqlite, so no database setup is required.

To initialize the schema and initial data, run in the Clusive\target directory:
* `python manage.py migrate`
* `python manage.py loaddata preferencesets tiptypes callstoaction subjects` 

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

Some initial **Teacher resources** are available in the Clusive\resources directory.
For these resources, a JSON file listing them along with important metadata
is required.  The default resources can be imported with the following command:
* `python manage.py import_resources ..\resources\resources.json`

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

## Running Cypress tests

* Run the standard local install. This will install Cypress as a dev dependency.
* In the Clusive\target directory, run `python manage.py createrostersamples` if you have not already.
  The tests depend on logging in as one of these test users.
* Run `npx cypress open` from the root to interactively run the tests.
* For IntelliJ users, the "Cypress Support" plugin is helpful.

## Connecting Google Authentication

To allow users to log in with their Google account, 
there are several additional steps.

1. Create a Project in the [Google Cloud Console](https://console.cloud.google.com).
2. Enable the Google Classroom API
3. Configure the authentication on the "OAuth Consent Screen" page in the 
     "APIs and Services" section of the Console.  The "EDIT APP" link at the top
     of the "OAuth Consent Screen" provides an "Edit app registration"
     step-by-step process for filling in the information.
4. Required scopes (step 2 of the "Edit app registration"):
     * `auth/userinfo.email`
     * `auth/userinfo.profile`
     * `auth/classroom.courses.readonly`
     * `auth/classroom.rosters.readonly`
     * `auth/classroom.profile.emails`
5. Create an "OAuth client ID" on the "Credentials" page, which is also in the
     "APIs and Services" section of the Console.
     * Application type is "Web application"
     * Authorized JavaScript origins should be the URL of your instance, eg `https://clusive.cast.org`.
     * Authorized redirect URIs should list two URIs: your instance with the paths '/accounts/google/login/callback/' and '/account/add_scope_callback/',
       eg 
       * `https://clusive.cast.org/accounts/google/login/callback/`
       * `https://clusive.cast.org/account/add_scope_callback/`
     * When created, take note of the Client ID and Client Secret.
6. Add the Google "provider" to Clusive as [documented](https://django-allauth.readthedocs.io/en/latest/providers.html#django-configuration) for the Django-allauth module. There are a few different ways to do this. The manual method is as follows:
    * Log in to your instance as an administrator.
    * Go to "Social Applications", click Add, and set:
      * provider: Google
      * name: Google
      * Client id: from step 5, above.
      * Secret key: "Client Secret" from step 5.
      * Key: leave blank.
      * Chosen sites: add the default site (if you haven't changed anything, this will be called "example.com" and have ID=1).
    * Set up the "Sites" record
      * This is the record for the default site chosen in the previous step, initially called "example.com".
      * Go to the top-level "Sites" and choose "example.com".
      * Set the `Domain Name` field to:
        * "localhost:8000", if this setup is for local development, and you are running Clusive on "localhost" and using port 8000.
          Note that the domain name must match the actual domain name exactly.  That is, if the server is using "localhost", do
          not specify "127.0.0.1" for the domain name in the Sites record.
        * In general, the `Domain Name` must match the host and port of your Clusive server.  For example, if the server
          is running on "clusive.abcxyz.org" (no port), then use that for the `Domain Name`.
      * You can change the `Display Name` from "example.com" to something more meaningful to your situation, but it
        does not really matter.

## Connecting to Bookshare

Optional. In order to allow users to download books from their Bookshare accounts,
you would need to obtain a Bookshare API key from Benetech. 
If you have one, in Clusive's admin interface, go to "Social Applications", click Add, and set:
* Provider: Bookshare
* Name: bookshare
* Client ID: your API key
* Sites: add your site

## Connecting to Merriam Webster

Optional. A fallback to a custom dictionary entry includes definitions from the Merriam-Webster 
Intermediate Dictionary.  To use Merriam-Webster your installation must apply for a Merriam-Webster 
API key directly from [Merriam Webster](https://dictionaryapi.com/register/index).  
The API key must be supplied into the settings file variable MERRIAM_WEBSTER_API_KEY.

## Connecting to MailChimp

Optional. [Mailchimp](https://mailchimp.com/) has been integrated to communicate via email with users
of the application. To connect with Mailchimp the API key, the server, and the email list 
must be provided.  These fields are supplied into the settings file as the variables: MAILCHIMP_API_KEY,
MAILCHIMP_SERVER, and MAILCHIMP_EMAIL_LIST_ID.

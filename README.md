# Clusive

_Clusive_ is an adaptive, customizable, accessible web-based EPUB reader 
built for education.  Our goal is to provide options and supports so that every student can 
succeed in learning.

Clusive is a project of the [Center for Inclusive Software for Learning](https://cisl.cast.org), 
which is funded by the US Department of Education (*), 
and run by [CAST](https://www.cast.org), 
[SRI Education](http://www.sri.com/about/organization/education), 
and the [IDRC](http://idrc.ocadu.ca/).  
For more on the project and its goals, or to get involved, visit 
the [CISL project website](https://cisl.cast.org). 

## Current status

* Accounts can be created by the administrator, by email-based self-registration, or users can log in with a Google account.
* Teachers and parents can set up student/child accounts, organized into groups or classrooms. Rosters can also be imported from Google Classroom.
* Includes a Dashboard, searchable Library page, Reading page, and Word Bank.
* User can customize the color scheme, font size, font style, line spacing, letter spacing, read-aloud voice and speed, and translation language.
* Any word can be looked up in a built-in dictionary.
* Read-aloud using local text-to-speech and translation using Google Translate are available.
* Content can be highlighted and annotated.
* Adaptive glossary functionality which probes user knowledge of key 
vocabulary words, tracks the user's knowledge and interest in specific vocabulary words,
and provides customized supports based on this.
* Accessible, mobile-friendly interface.
* Over 300 public-domain and openly-licensed EPUB documents are provided by default in the library.
We have added images and custom glossary words with definitions to many of these. 
Instructions are provided for adding your own documents.
* Users can also upload their own EPUBs for private or classroom use.

## Installation

Please see the [installation directions](https://github.com/cast-org/clusive/blob/master/INSTALL.md).

## Architecture

The web application is built in Python with [Django](https://www.djangoproject.com/).

EPUB reading functions are based on [Readium 2](https://readium.org/development/readium-2-overview/),
specifically the R2 web-reader [R2D2BC](https://github.com/d-i-t-a/R2D2BC).

We use the [Figuration](http://figuration.org) front-end framework in conjunction with the Infusion [Preferences Framework](https://build.fluidproject.org/infusion/demos/prefsFramework/).

Word definitions are provided by [WordNet](https://wordnet.princeton.edu/).

## License

Clusive is open source. It is made available under the [BSD 3-clause license](https://opensource.org/licenses/BSD-3-Clause).
Your contributions in the form of suggestions, bug reports, or pull requests are welcome!

----
(*) This content was developed under a grant from the US Department of Education, #H327A170002.
However, the contents do not necessarily represent the policy of the US Department
of Education, and you should not assume endorsement by the Federal Government. 
Project Officer, Celia Rosenquist.


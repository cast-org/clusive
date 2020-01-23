# Clusive

_Clusive_ is an adaptive, customizable, accessible web-based EPUB reader 
built for education.  Our goal is to provide options and supports so that every student can 
succeed in learning.  It will eventually be part of a suite of tools, including 
authoring and preferences discovery.

Clusive is a project of the [Center for Inclusive Software for Learning](http://cisl.cast.org), 
a project funded by the US Department of Education (*), 
and run by [CAST](http://www.cast.org), 
[SRI Education](http://www.sri.com/about/organization/education), 
and the [IDRC](http://idrc.ocadu.ca/).  
For more on the project and its goals, or to get involved, visit 
the [CISL project website](http://cisl.cast.org). 

## Current status

* Works with manually created or temporary guest logins; no self-registration yet.
* Library page and reading interface is functional for single-chapter EPUB content.
* User can customize the color scheme, font size, font style, 
line spacing, and letter spacing.
* Any word can be looked up in a built-in dictionary.
* Prototype of "adaptive glossary" functionality, which probes user knowledge of key 
vocabulary words, tracks the user's knowledge and interest in specific vocabulary words,
and provides customized supports based on this.
* Accessible, mobile-friendly interface.
* 16 EPUB documents are provided, mostly from the openly-licensed 
[SERP Word Generation](https://www.serpinstitute.org/wordgen-elementary) curriculum.
We have added images and custom glossary words with definitions to these. 
Instructions are provided for adding your own documents.

## Installation

Please see the [installation directions](https://github.com/cast-org/clusive/blob/master/INSTALL.md).

## Architecture

The web application is built in Python with [Django](https://www.djangoproject.com/).

EPUB reading functions are based on [Readium 2](https://readium.org/development/readium-2-overview/),
specifically the R2 web-reader [R2D2BC](https://github.com/d-i-t-a/R2D2BC).

We use the [Figuration](http://figuration.org) front-end framework.

Word definitions are provided by [Wordnet](https://wordnet.princeton.edu/).

## License

Clusive is open source. It is made available under the [BSD 3-clause license](https://opensource.org/licenses/BSD-3-Clause).
Your contributions in the form of suggestions, bug reports, or pull requests are welcome!

----
(*) This content was developed under a grant from the US Department of Education, #H327A170002.
However, the contents do not necessarily represent the policy of the US Department
of Education, and you should not assume endorsement by the Federal Government. 
Project Officer, Tara Courchaine, Ed.D.


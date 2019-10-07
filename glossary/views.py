import logging
from django.shortcuts import render

from django.http import JsonResponse, HttpResponseNotFound
from wordnet import util as wordnetutil

logger = logging.getLogger(__name__)


# Note, currently these views depend directly on Wordnet.
# Eventually, the goal is to have multiple possible backends and a way to
# configure which one(s) to use.

def lookup(request, word='hi'):
    defs = wordnetutil.lookup(word)
    logger.debug("Wordnet returns: %s", defs)
    if defs:
        return JsonResponse(defs)
    else:
        return HttpResponseNotFound("<p>No definition found</p>")


def glossdef(request, word):
    defs = wordnetutil.lookup(word)
    if defs:
        return render(request, 'glossary/glossdef.html', context=defs)
    else:
        return HttpResponseNotFound("<p>No definition found</p>")

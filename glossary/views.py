import logging
from django.shortcuts import render

from django.http import JsonResponse, HttpResponseNotFound

from glossary.apps import GlossaryConfig
from wordnet import util as wordnetutil
from eventlog.signals import vocab_lookup

logger = logging.getLogger(__name__)

# Note, currently these views depend directly on Wordnet.
# Eventually, the goal is to have multiple possible backends and a way to
# configure which one(s) to use.

def lookup(request, word):
    """Generic lookup function that returns JSON data.
    Currently unused."""
    defs = wordnetutil.lookup(word)
    if defs:
        return JsonResponse(defs)
    else:
        return HttpResponseNotFound("<p>No definition found</p>")


def glossdef(request, word):
    """Return a formatted HTML representation of a word's meaning(s)."""
    defs = wordnetutil.lookup(word)
    vocab_lookup.send(sender=GlossaryConfig.__class__,
                      session=request.session,
                      value=word,
                      )
    # TODO might want to record how many meanings were found (especially if it's 0): len(defs['meanings'])
    if defs:
        return render(request, 'glossary/glossdef.html', context=defs)
    else:
        return HttpResponseNotFound("<p>No definition found</p>")

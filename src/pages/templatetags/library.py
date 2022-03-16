import re
from urllib.parse import urlencode

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def search_args(query, subject):
    """
    Build URL args for the library page from the given query and subject filter.
    """
    params = []

    if query:
        params.append(('query', query))

    if subject:
        params.append(('subjects', subject))

    return "?%s" % (urlencode(params))


@register.filter(is_safe=True)
@stringfilter
def highlight(text, search):
    """
    Highlight (with class="highlighted") all occurrences of a search string in the input.
    """
    if search:
        highlighted = re.sub('(?i)(%s)' % (re.escape(search)),
                             '<span class="highlight">\\1</span>',
                             text)
        return mark_safe(highlighted)
    else:
        return mark_safe(text)


@register.filter(is_safe=True)
def period_names(assignment_list):
    return ", ".join([p.period.name for p in assignment_list])
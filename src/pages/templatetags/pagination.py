from urllib.parse import urlencode

from django import template

register = template.Library()

@register.simple_tag
def pagination_search(url, query, subject):
    """
    Build URL for the library page including search and filter parameters, and sort option.
    """
    params = []

    if query:
        params.append(('query', query))

    if subject:
        params.append(('subjects', subject))

    return "%s?%s" % (url, urlencode(params))

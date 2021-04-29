from django import template
register = template.Library()

@register.simple_tag
def pagination_search(url, page, query, filters):
    """
    Build URL for the library page including pagination, search and filter parameters, and sort option.
    """
    params = []

    if query:
        params.append('query=%s' % query)
    else:
        params.append('query=')

    if page:
        params.append('page=%s' % page)

    if filters:
        params.append('filter=%s' % filters)

    if params:
        return "%s?%s" % (url, "&".join(params))
    else:
        return url

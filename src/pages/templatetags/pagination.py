from django import template
register = template.Library()

@register.simple_tag
def pagination_search(url, page, query):
    """
    Build URL for pagination that passes optional search query
    """

    if query and page:
        return '%s?query=%s&page=%s' % (url, query, page)

    if query:
        return '%s?query=%s' % (url, query)

    if page:
        return '%s?page=%s' % (url, page)

    return url
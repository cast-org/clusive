import re

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter(is_safe=True)
@stringfilter
def formcontrol(value):
    """
    Adds the form-control class attribute to the first <input> found.
    This gives it the Figuration look and feel.
    """

    match = re.search(r'<input.*?>', value)
    input = match.group()
    classmatch = re.search(r'class="', input)
    if classmatch:
        newinput = input[:classmatch.start()] + 'class="form-control ' + input[classmatch.end():]
    else:
        newinput = input[:-1] + 'class="form-control">'

    return value[:match.start()] + newinput + value[match.end():]


@register.filter(is_safe=True)
@stringfilter
def formlabel(value):
    """
    Adds the form-label class attribute to the first <label> found.
    This gives it the Figuration look and feel.
    """

    match = re.search(r'<label.*?>', value)
    input = match.group()
    classmatch = re.search(r'class="', input)
    if classmatch:
        newinput = input[:classmatch.start()] + 'class="form-label ' + input[classmatch.end():]
    else:
        newinput = input[:-1] + 'class="form-label">'

    return value[:match.start()] + newinput + value[match.end():]
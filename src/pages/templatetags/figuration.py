import re

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()


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
@stringfilter
def formcontrol(value):
    """
    Adds the form-control class attribute to the first <input> found.
    This gives it the Figuration look and feel.
    """

    match = re.search(r'<(input|textarea).*?>', value)
    if match:
        input = match.group()
        typematch  = re.search(r'type="(.*?)"', input)
        type = typematch.group(1) if typematch else 'text'
        classmatch = re.search(r'class="', input)
        if type=='checkbox' or type=='radio':
            addclass = 'form-check-input'
        else:
            addclass = 'form-control'

        if classmatch:
            newinput = '%sclass="%s %s' % (input[:classmatch.start()], addclass, input[classmatch.end():])
        else:
            newinput = '%s class="%s">' % (input[:-1], addclass)

        return value[:match.start()] + newinput + value[match.end():]
    else:
        return value

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
        newinput = input[:-1] + ' class="form-label">'

    return value[:match.start()] + newinput + value[match.end():]
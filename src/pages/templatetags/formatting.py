import re

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(is_safe=True)
def duration(td):
    """Nicely format the Timedelta for humans to read"""
    if td:
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        if hours:
            return '{} hour{} {} minute{}'.format(hours, "s" if hours!=1 else "", minutes, "s" if minutes!=1 else "")
        elif minutes:
            return '{} minute{}'.format(minutes, "s" if minutes!=1 else "")
        else:
            return '<1 minute'
    else:
        return '0'


@register.filter(is_safe=True)
@stringfilter
def add_icons(text):
    """
    If there are any strings of the form {icon:foo} in the input, replace with a glyph from the icon library.
    For example, given input "Here is a star: {{icon:starred}},
    this generates "Here is a star: <span class="icon-starred" aria-hidden="true"></span>."

    :param text: input text
    :return: replacement text
    """
    interpolated = re.sub('{icon:([^}]+)}',
                          '<span class="icon-\\1" aria-hidden="true"></span>',
                          text)
    return mark_safe(interpolated)

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter(is_safe=True)
def list_index(sequence, position):
    try:
        return sequence[position]
    except:
        return None

@register.filter(is_safe=True)
def list_index_prev(sequence, position):
    if 0 >= position:
        return None
    try:
        return sequence[int(position) - 1]
    except:
        return None

@register.filter(is_safe=True)
def list_index_next(sequence, position):
    if len(sequence) - 1 == position:
        return None
    try:
        return sequence[int(position) + 1]
    except:
        return None
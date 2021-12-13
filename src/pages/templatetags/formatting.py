from django import template

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

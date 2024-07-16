from django import template

register = template.Library()


@register.filter
def replace_and_upper(value):
    return value.upper().replace("_", " ")


@register.filter
def replace(value):
    return value.replace("_", " ")

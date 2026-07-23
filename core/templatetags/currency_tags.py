from django import template
from core.utils import format_currency
register = template.Library()

@register.filter
def currency(value, restaurant):
    return format_currency(value, restaurant)
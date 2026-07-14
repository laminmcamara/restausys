from django import template
from core.utils import format_currency
register = template.Library()

@register.filter
def currency(value, currency_code):
    return format_currency(value, currency_code)
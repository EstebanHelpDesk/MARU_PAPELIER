
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Permite acceder a valores de un diccionario desde el template."""
    return dictionary.get(key, '')
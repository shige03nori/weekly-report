from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """辞書からキーで値を取得するテンプレートフィルター"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''

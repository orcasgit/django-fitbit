from django import template

from .. import utils


register= template.Library()


@register.filter
def is_integrated_with_fitbit(user):
    return utils.is_integrated(user)

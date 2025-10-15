from django import template
import math
register = template.Library()

@register.simple_tag
def discount_calculation(price, discount):
    if discount is None or discount is 0:
        return price
    #sellprice = price
    sellprice = price - (price * discount / 100)
    return math.ceil(sellprice)

@register.filter
def duration_format(value):
    """
    Convert seconds (int) to H:MM:SS format.
    Example: 3670 -> 1:01:10
    """
    try:
        total_seconds = int(value or 0)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    except (TypeError, ValueError):
        return "0:00"

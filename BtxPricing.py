"""Integer credit pricing for microphone ticker messages."""
from decimal import Decimal, InvalidOperation, ROUND_CEILING


def btx_price(text: str, rate) -> int:
    """Count Unicode code points, including spaces; round the total up once."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError('A message is required')
    try:
        price = Decimal(str(rate))
    except (InvalidOperation, ValueError) as error:
        raise ValueError('Invalid credit rate') from error
    if not price.is_finite() or price < 0 or price.as_tuple().exponent < -2:
        raise ValueError('Credit rate must be non-negative with at most two decimal places')
    return int((price * len(text)).to_integral_value(rounding=ROUND_CEILING))

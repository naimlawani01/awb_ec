"""Convert number to French words for invoice amounts."""

UNITS = ['', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf']
TENS = ['', 'dix', 'vingt', 'trente', 'quarante', 'cinquante', 'soixante', 'soixante',
        'quatre-vingt', 'quatre-vingt']
TEN_UNITS = ['', 'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize', 'dix-sept',
             'dix-huit', 'dix-neuf']


def _to_words_under_100(n: int) -> str:
    if n == 0:
        return ''
    if n < 10:
        return UNITS[n]
    if n < 20:
        return TEN_UNITS[n - 10]
    tens = n // 10
    units = n % 10
    if tens == 7:
        return 'soixante-' + ('dix' if units == 0 else (TEN_UNITS[units] or UNITS[units]))
    if tens == 9:
        return 'quatre-vingt-' + ('' if units == 0 else UNITS[units])
    return TENS[tens] + ('-' + UNITS[units] if units > 0 else '')


def _to_words_under_1000(n: int) -> str:
    if n == 0:
        return ''
    hundreds = n // 100
    rest = n % 100
    result = ''
    if hundreds > 0:
        result = 'cent' if hundreds == 1 else f'{UNITS[hundreds]} cent'
        if rest > 0:
            result += ' '
    if rest > 0:
        result += _to_words_under_100(rest)
    return result


def number_to_french_words(n: float) -> str:
    """Convert number to French words (e.g. for invoice amounts)."""
    int_part = int(n)
    if int_part == 0:
        return 'zéro'
    if int_part >= 1_000_000_000:
        return str(int_part)

    millions = int_part // 1_000_000
    thousands = (int_part % 1_000_000) // 1_000
    units = int_part % 1_000

    parts = []
    if millions > 0:
        m = 'million' if millions == 1 else 'millions'
        parts.append(f'{_to_words_under_1000(millions)} {m}')
    if thousands > 0:
        t = _to_words_under_1000(thousands)
        parts.append('mille' if t == 'un' else f'{t} mille')
    if units > 0:
        parts.append(_to_words_under_1000(units))

    result = ' '.join(parts)
    return result[0].upper() + result[1:] if result else result

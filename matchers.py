def any_matcher(ch):
    """Matches any object."""
    return True

def newline_matcher(ch):
    return ch in '\n\r'

default_matchers = {
    'any': any_matcher,
    'space': str.isspace,
    'digit': str.isdigit,
    'alnum': str.isalnum,
    'newline': newline_matcher,
}

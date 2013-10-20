def any_matcher(ch):
    """Matches any object."""
    return True

def newline_matcher(ch):
    return ch in '\n\r'

def proper_space_matcher(ch):
    return ch.isspace() and not newline_matcher(ch)

_default_matchers = {
    'any': any_matcher,
    'space': str.isspace,
    'digit': str.isdigit,
    'alnum': str.isalnum,
    'newline': newline_matcher,
    'propsp': proper_space_matcher,
}

class InverseMatcher:
    def __init__(self, matcher):
        self.matcher = matcher
    
    def __call__(self, ch):
        return not self.matcher(ch)

default_matchers = dict(_default_matchers)
for name, matcher in _default_matchers.iteritems():
    default_matchers['-' + name] = InverseMatcher(matcher)

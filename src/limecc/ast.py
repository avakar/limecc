import inspect

class Node:
    def __init__(self, **kw):
        for k in self.keys():
            v = kw.pop(k)
            setattr(self, k, v)

    def keys(self):
        for base in inspect.getmro(type(self)):
            if base is None:
                break
            yield from getattr(base, '__annotations__', ())

    def items(self):
        for k in self.keys():
            v = getattr(self, k)
            yield (k, v)

    def clone(self):
        return type(self)(**dict(self.items()))

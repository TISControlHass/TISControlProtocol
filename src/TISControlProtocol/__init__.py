import base64

def alpha__(x):
    return base64.b64decode(x).decode()

def beta__(y, **z):
    w = base64.b64decode(y).decode()
    return w.format(**z)
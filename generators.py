def star_footnotes():
    i = 1
    while True:
        yield '*' * i  # can be converted to dict if we'll need additional parms
        i += 1


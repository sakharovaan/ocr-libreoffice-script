import uno
import logging

from elements import Document, Paragraph, Footnote
from parsers import middle_dash_between_digits, canonic_links

"""
Current limitations:
a) doesn't recognise footnotes continuing on other page
"""


def get_model():
    """
    An adjustable current document getter

    :return: current model
    """
    # get the uno component context from the PyUNO runtime
    localContext = uno.getComponentContext()

    # create the UnoUrlResolver
    resolver = localContext.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", localContext)

    # connect to the running office
    ctx = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
    smgr = ctx.ServiceManager

    # get the central desktop object
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

    # access the current writer document
    model = desktop.getCurrentComponent()

    return model


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    model = get_model()
    document = Document().from_model(model)
    #document.strip_empty()
    #document.strip_custom(lambda x: not(len(x) == 3 and str(x).isdecimal()))  # page numbers
    #document.strip_footnotes(('*'*(i+1) for i in range(1000)))
    #document.check(lambda x: len(x) > 60, "Too short paragraph ")
    #document.replace_footnotes(('*'*(i+1) for i in range(1000)))
    #document.merge_paragraphs()
    #document.prepare_paragraphs(middle_dash_between_digits)
    #document.prepare_footnotes(middle_dash_between_digits)
    #document.prepare_paragraphs(canonic_links)
    #document.prepare_footnotes(canonic_links)

    print(document)



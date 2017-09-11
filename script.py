import uno
import logging

from elements import Document
from parsers.middle_dash_between_digits import middle_dash_between_digits
from parsers.canonic_links import canonic_links
from generators import star_footnotes


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
    document.strip_empty()
    document.strip_custom(lambda x: not(len(x) == 3 and str(x).isdecimal()), use_tagged=False)  # page numbers
    document.strip_footnotes(star_footnotes())
    document.check(lambda x: len(x) > 60, "Too short paragraph ")
    document.replace_footnotes(star_footnotes())
    document.merge_paragraphs()
    document.prepare_paragraphs(middle_dash_between_digits)
    document.prepare_footnotes(middle_dash_between_digits)
    document.prepare_paragraphs(canonic_links)
    document.prepare_footnotes(canonic_links)
    document.write("out.odt")
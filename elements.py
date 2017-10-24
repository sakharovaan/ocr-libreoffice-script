import logging
import textwrap
import uno
import re
from os import path

TAG_RE = re.compile(r'{{(\S*?)}}')
TAGS = dict(
    open_bold='{{b}}',
    close_bold='{{/b}}',
    open_italic='{{i}}',
    close_italic='{{/i}}',
    open_underline='{{u}}',
    close_underline='{{/u}}'
)


class Document:
    def __init__(self):
        self.paragraphs = []
        self.footnotes = []

    def _decide_tag(self, word, old_fmt_dict, new_fmt_dict):
        """
        Decide tagging for current word

        :param word: a word to use with tag
        :param old_fmt_dict: fmt_dict for previous word
        :param new_fmt_dict: fmt_dict for this word
        :return:
        """

        formats = dict(
            bold=dict(open=TAGS['open_bold'], close=TAGS['close_bold']),
            italic=dict(open=TAGS['open_italic'], close=TAGS['close_italic']),
            underlined=dict(open=TAGS['open_underline'], close=TAGS['close_underline'])
        )

        for k, v in formats.items():
            if old_fmt_dict[k] and not new_fmt_dict[k]:
                word = v['close'] + word
            elif not old_fmt_dict[k] and new_fmt_dict[k]:
                word = v['open'] + word

        return word

    def _reverse_decide_tag(self, tag, style):
        """
        Decide what this tag in text supposed to mean

        :param tag: tag without braces
        :param style: dict with styles
        :return: dict(style=style dict, put_footnote=number of footnote to put (if should))
        """
        warnings = ""

        if tag.isdecimal():  # is it footnote tag?
            return {'warnings': None, 'put_footnote': int(tag), 'style': style}

        for key, val in TAGS.items():  # is it style tag?
            if val == '{{%s}}' % tag:
                if key == 'open_bold':
                    if style['bold']:
                        warnings += "Unclosed tag %s " % tag

                    style['bold'] = True
                    break
                elif key == 'close_bold':
                    if not style['bold']:
                        warnings += "Orphaned tag %s " % tag

                    style['bold'] = False
                    break
                elif key == 'open_italic':
                    if style['italic']:
                        warnings += "Unclosed tag %s " % tag

                    style['italic'] = True
                    break
                elif key == 'close_italic':
                    if not style['italic']:
                        warnings += "Orphaned tag %s " % tag

                    style['italic'] = False
                    break
                elif key == 'open_underline':
                    if style['underlined']:
                        warnings += "Unclosed tag %s " % tag

                    style['underlined'] = True
                    break
                elif key == 'close_underline':
                    if not style['underlined']:
                        warnings += "Orphaned tag %s " % tag

                    style['underlined'] = False
                    break
        else:
            return

        return {'warnings': warnings, 'put_footnote': None, 'style': style}

    def from_model(self, model):
        ctrl = model.getCurrentController()
        text = model.Text
        cursor = text.createTextCursor()
        view_cursor = ctrl.getViewCursor()
        enum = text.createEnumeration()

        while enum.hasMoreElements():
            # iterate over all paragraphs
            paragraph = enum.nextElement()

            text = ""
            text_untagged = ""
            format_dict = dict(bold=False, italic=False, underlined=False)

            cursor.gotoRange(paragraph.getStart(), False)
            view_cursor.gotoRange(paragraph.getStart(), False)

            # iterate over words and save their formatting

            par_enum = paragraph.createEnumeration()
            while par_enum.hasMoreElements():  # usually this is a word or part of it with unique formatting
                par_el = par_enum.nextElement()

                new_fmt_dict = dict(bold=par_el.CharWeight > 100,
                                    italic=par_el.CharPosture.value == 'ITALIC',
                                    underlined=par_el.CharUnderline > 0)  # style of current word

                text += self._decide_tag(par_el.String, format_dict, new_fmt_dict)
                text_untagged += par_el.String
                format_dict = new_fmt_dict

            else:
                text += self._decide_tag('', format_dict, dict(bold=False, italic=False, underlined=False))

            self.paragraphs.append(Paragraph(view_cursor.getPage(), text, text_untagged, paragraph))

        return self

    def check(self, func, message, fail=False):
        """
        Iterate over paragraphs and check whether func is true

        :param func: custom func to check
        :param message: message to display
        :param fail: exception or warning
        """
        for paragraph in self.paragraphs:
            if not func(paragraph.text):
                if fail:
                    raise Exception("%s (para %s)" % (message, paragraph))
                else:
                    logging.warning("%s (para %s)" % (message, paragraph))

    def strip_empty(self):
        return self.strip_custom(lambda x: x, use_tagged=False)

    def strip_custom(self, func, use_tagged=True):
        """
        Strip paragraphs matching to a custom function(text) -> true if keep, falsy if get rid of

        :param func: custom function
        :param use_tagged: use tagged or untagged version of paragraph's text
        """
        new_pars = []

        for paragraph in self.paragraphs:

            if use_tagged:
                attr = 'text'
            else:
                attr = 'text_untagged'

            if func(getattr(paragraph, attr)):
                new_pars.append(paragraph)
            else:
                logging.info("[INFO] Discarding paragraph %s" % paragraph)

        self.paragraphs = new_pars
        return self

    def strip_footnotes(self, generator, max_gen=20):
        """
        Decide which paragraphs are footnotes and split them into other array

        :param starts_with: a sign with what footnotes starts
        :return:
        """
        gen_arr = [next(generator) for i in range(max_gen)]

        new_pars = []
        footnote_num = 0
        cur_page = 1

        for paragraph in self.paragraphs:
            if paragraph.page_num != cur_page:
                # new page
                footnote_num = 0
                cur_page = paragraph.page_num

            if not str(paragraph.text_untagged).startswith(gen_arr[footnote_num]):
                if footnote_num == 0:
                    # ordinary paragraph

                    new_pars.append(paragraph)

                else:
                    # continuation of previous paragraph

                    self.footnotes[-1:][0] += Footnote(paragraph.page_num,
                                                       paragraph.text,
                                                       paragraph.text_untagged,
                                                       None,
                                                       footnote_num - 1)
            else:
                # a new footnote
                self.footnotes.append(Footnote(paragraph.page_num,
                                               paragraph.text,
                                               paragraph.text_untagged,
                                               gen_arr[footnote_num],
                                               footnote_num))
                footnote_num += 1

        self.paragraphs = new_pars
        return self

    def replace_footnotes(self, generator, max_gen=20):
        """
        Replace links to footnotes in paragraph with whole-document numeration tags, also check numeration

        :param generator: generator expression used to replace
        :param max_gen: maximum amount of footnotes on page
        """
        gen_arr = [next(generator) for i in range(max_gen)]
        footnotes_q = {}

        # count footnotes
        for footnote in self.footnotes:
            if footnote.page_num in footnotes_q:
                footnotes_q[footnote.page_num] += 1
            else:
                footnotes_q[footnote.page_num] = 1

        cur_page = 1
        current_count = 0
        total_count = 0
        for i, paragraph in enumerate(self.paragraphs):
            if paragraph.page_num != cur_page:
                # new page, check previous and reset counters
                if cur_page not in footnotes_q and current_count:
                    logging.warning("There are %s links on page %s and %s footnotes found" % (current_count,
                                                                                              cur_page,
                                                                                              footnotes_q.get(cur_page,
                                                                                                              0)))
                elif cur_page in footnotes_q and footnotes_q[cur_page] != current_count:
                    logging.warning("There are %s links on page %s and %s footnotes found" % (current_count,
                                                                                              cur_page,
                                                                                              footnotes_q.get(cur_page,
                                                                                                              0)))

                cur_page = paragraph.page_num
                current_count = 0

            while gen_arr[current_count] in paragraph.text:
                total_count += 1
                self.paragraphs[i].text = str(paragraph.text).replace(gen_arr[current_count],
                                                                      "{{%s}}" % total_count, 1)
                current_count += 1

        if total_count != len(self.footnotes):
            logging.warning("We got %s links in document and %s footnotes, check logs for warnings" % (total_count,
                                                                                                       len(
                                                                                                           self.footnotes)))
        else:
            logging.info("There are %s footnotes for now" % total_count)

        return self

    def merge_paragraphs(self):
        """
        Iterate over paragraphs and compile those which were split
        Do only when you don't care about original page ordering anymore!
        """
        new_pars = []

        for paragraph in self.paragraphs:
            if not str(paragraph.text_untagged[0]).isupper() and len(new_pars) > 0:
                logging.info("[CHANGED] Merging paragraphs %s and %s", new_pars[-1:][0], paragraph)
                new_pars[-1:][0] += paragraph
            else:
                new_pars.append(paragraph)

        self.paragraphs = new_pars

        return self

    def prepare_paragraphs(self, func, apply_on_untagged=True):
        """
        Replace output of given func as text to all paragraphs

        :param func: custom func
        :param apply_on_untagged: apply also on untagged version
        :return:
        """
        for i, paragraph in enumerate(self.paragraphs):
            logging.info("[START] Apply %s on paragraph %s (tagged version)", func.__name__, paragraph)
            self.paragraphs[i].text = func(paragraph.text)

            if apply_on_untagged:
                logging.info("[START] Apply %s on paragraph %s (untagged version)", func.__name__, paragraph)
                self.paragraphs[i].text_untagged = func(paragraph.text_untagged)

        return self

    def prepare_footnotes(self, func, apply_on_untagged=True):
        """
        Replace output of given func as text to all footnotes

        :param func:
        :param apply_on_untagged: apply also on untagged version
        :return:
        """
        for i, footnote in enumerate(self.footnotes):
            logging.info("[START] Apply %s on footnote %s (tagged version)", func.__name__, footnote)
            self.footnotes[i].text = func(footnote.text)
            if apply_on_untagged:
                logging.info("[START] Apply %s on footnote %s (untagged version)", func.__name__, footnote)
                self.footnotes[i].text_untagged = func(footnote.text_untagged)

    def _write_paragraph(self, paragraph, document, cursor, styling):
        tag = ""
        buffer = ""
        flush_buffer = False

        put_footnote = None
        text = document.Text
        for i, letter in enumerate(paragraph.text):
            if letter == '{' and paragraph.text[i:i + 2] == '{{':
                tag = re.search(TAG_RE, paragraph.text[i:i + 15])
                if not tag:
                    logging.warning("[WARNING] False-positive tag search on %s", paragraph.text[i:i + 15])
                else:
                    tag = tag.group(1)
                    result = self._reverse_decide_tag(tag, styling)
                    if not result:
                        logging.warning("[WARNING] Unknown tag %s", tag)
                    else:
                        styling = result['style']
                        put_footnote = result['put_footnote']
                        if result['warnings']:
                            logging.warning("[WARNING] %s", result['warnings'])

                tag = "{{%s}}" % tag  # for tag omitting

                flush_buffer = True

            # put footnote before omitting
            if put_footnote:
                footnote = document.createInstance("com.sun.star.text.Footnote")
                text.insertTextContent(cursor, footnote, 0)
                footnote_cursor = footnote.Text.createTextCursor()
                self._write_paragraph(self.footnotes[put_footnote - 1], footnote, footnote_cursor)
                put_footnote = None

            # omit tag symbol by symbol
            if tag:
                if tag[:1] == letter:
                    tag = tag[1:]
                    continue
                else:
                    logging.warning("[WARNING] tag (%s) and document (%s) letters mismatch",
                                    tag, paragraph.text[i:i + 15])

            # FIXME wrong style preservation on next paragraph

            if flush_buffer:
                text.insertString(cursor, buffer, 0)
                buffer = ""
                flush_buffer = False

                if styling['bold']:
                    cursor.CharWeight = 150
                else:
                    cursor.CharWeight = 100

                if styling['italic']:
                    cursor.CharPosture = 'ITALIC'
                else:
                    cursor.CharPosture = 'NONE'

                if styling['underlined']:
                    cursor.CharUnderline = 1
                else:
                    cursor.CharUnderline = 0

            buffer += letter

        else:
            text.insertString(cursor, buffer, 0)

        return styling

    def write(self, filename):
        """
        Write content to file

        :param filename: file to write
        :return:
        """

        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        context = resolver.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext")
        desktop = context.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", context)

        url = "private:factory/swriter"

        document = desktop.loadComponentFromURL(url, "_blank", 0, ())
        text = document.Text
        styling = dict(
            italic=False,
            bold=False,
            underlined=False
        )

        cursor = text.createTextCursor()
        for paragraph in self.paragraphs:
            text.insertString(cursor, '\t', 0)
            styling = self._write_paragraph(paragraph, document, cursor, styling)
            text.insertString(cursor, '\r', 0)

        document.storeAsURL('file://' + path.realpath(filename), ())
        document.dispose()

        return self


class Paragraph:
    def __init__(self, page_num, text, text_untagged, origin):
        self.page_num = page_num
        self.text = text
        self.text_untagged = text_untagged
        self.origin = [origin]

    def __repr__(self):
        return "<Paragraph page:%s text: %s>" % (self.page_num,
                                                 textwrap.shorten(self.text_untagged, width=30))

    def __iadd__(self, other):
        self.text += " " + other.text
        self.text_untagged += " " + other.text_untagged
        self.origin.extend(other.origin)
        return self


class Footnote:
    def __init__(self, page_num, text, text_untagged, starts_with, num_on_page):
        self.page_num = page_num
        self.num_on_page = num_on_page
        self.text = self._cut_startswith(str(text).strip(), starts_with)
        self.text_untagged = self._cut_startswith(str(text_untagged).strip(), starts_with, tagged=False)

    def __repr__(self):
        return "<Footnote page:%s->%s text: %s>" % (self.page_num, self.num_on_page,
                                                    textwrap.shorten(self.text_untagged, width=30))

    def __iadd__(self, other):
        if other.num_on_page != self.num_on_page:

            raise Exception("Merge conflict of footnotes: %s + %s" % (self, other))

        else:
            self.text += other.text

    @staticmethod
    def _cut_startswith(text, starts_with, tagged=True):
        if starts_with:
            if tagged:
                for symbol in starts_with:
                    text = text.replace(symbol, '', 1)
            else:
                text = text.replace(starts_with, '', 1)

        return text

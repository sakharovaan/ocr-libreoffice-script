import logging


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

        formats = dict(  # with spaces for correct tokenizing
            bold=dict(open=' {{b}} ', close=' {{/b}} '),
            italic=dict(open=' {{i}} ', close=' {{/i}} '),
            underlined=dict(open=' {{u}} ', close=' {{/u}} ')
        )

        for k, v in formats.items():
            if old_fmt_dict[k] and not new_fmt_dict[k]:
                word = v['close'] + word
            elif not old_fmt_dict[k] and new_fmt_dict[k]:
                word = v['open'] + word

        return word

    def from_model(self, model):
        ctrl = model.getCurrentController()
        text = model.Text
        cursor = text.createTextCursor()
        view_cursor = ctrl.getViewCursor()
        enum = text.createEnumeration()
        transf = ctrl.getTransferable()

        format_dict = dict(bold=False, italic=False, underlined=False)

        while enum.hasMoreElements():
            # iterate over all paragraphs
            paragraph = enum.nextElement()

            text = ""
            prev_word_whitespace = ""
            word_string = ""
            cursor.gotoRange(paragraph.getStart(), False)
            view_cursor.gotoRange(paragraph.getStart(), False)

            # iterate over words and save their formatting

            while True:
                # TODO correct styling
                cursor.gotoEndOfWord(True)  # select only current word
                prev_word_whitespace = cursor.String  # only word
                new_fmt_dict = dict(bold=cursor.CharWeight > 100,
                                    italic=cursor.CharPosture.value == 'ITALIC',
                                    underlined=cursor.CharUnderline > 0)  # style of current word

                text += self._decide_tag(word_string, format_dict, new_fmt_dict)  # add word and its style
                if len(prev_word_whitespace) > 0:  # add whitespace with new style
                    text += self._decide_tag(prev_word_whitespace, format_dict, new_fmt_dict)

                format_dict = new_fmt_dict

                cursor.gotoEndOfWord(False)
                cursor.gotoNextWord(True)  # select all spacing and punctuation to next one
                word_string = cursor.String  # punctuation and such
                if cursor.isEndOfParagraph():
                    # close all tags and leave
                    text += self._decide_tag('', format_dict, dict(bold=False, italic=False, underlined=False))
                    break
                else:
                    cursor.gotoStartOfWord(False)  # reset selection from [curr-s;next-s] to [next-s;next-s]

            self.paragraphs.append(Paragraph(view_cursor.getPage(), text, paragraph))

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
        return self.strip_custom(lambda x: x)

    def strip_custom(self, func):
        """
        Strip paragraphs matching to a custom function(text) -> true if keep, falsy if get rid of

        :param func: custom function
        """
        new_pars = []

        for paragraph in self.paragraphs:
            if func(paragraph.text):
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

            if not str(paragraph.text).startswith(gen_arr[footnote_num]):
                if footnote_num == 0:
                    # ordinary paragraph

                    new_pars.append(paragraph)

                else:
                    # continuation of previous paragraph

                    self.footnotes[-1:][0] += Footnote(paragraph.page_num, paragraph.text, None, footnote_num - 1)
            else:
                # a new footnote
                self.footnotes.append(Footnote(paragraph.page_num, paragraph.text, gen_arr[footnote_num], footnote_num))
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
            if not str(paragraph.text[0]).isupper() and len(new_pars) > 0:
                new_pars[-1:][0] += paragraph
            else:
                new_pars.append(paragraph)

        self.paragraphs = new_pars

        return self

    def prepare_paragraphs(self, func):
        """
        Replace output of given func as text to all paragraphs

        :param func:
        :return:
        """
        for i, paragraph in enumerate(self.paragraphs):
            self.paragraphs[i].text = func(paragraph.text)

        return self

    def prepare_footnotes(self, func):
        """
        Replace output of given func as text to all footnotes

        :param func:
        :return:
        """
        for i, footnote in enumerate(self.footnotes):
            self.footnotes[i].text = func(footnote.text)

        return self


class Paragraph:
    def __init__(self, page_num, text, origin):
        self.page_num = page_num
        self.text = text
        self.origin = [origin]

    def __repr__(self):
        return "<Paragraph page:%s text: %s>" % (self.page_num, self.text)

    def __iadd__(self, other):
        self.text += " " + other.text
        self.origin.extend(other.origin)
        return self


class Footnote:
    def __init__(self, page_num, text, starts_with, num_on_page):
        self.page_num = page_num
        self.num_on_page = num_on_page
        if starts_with:
            self.text = str(text).strip().replace(starts_with, '', 1)
        else:
            self.text = str(text).strip()

    def __repr__(self):
        return "<Footnote page:%s->%s text: %s>" % (self.page_num, self.num_on_page, self.text)

    def __iadd__(self, other):
        if other.num_on_page != self.num_on_page:

            raise Exception("Merge conflict of footnotes: %s + %s" % (self, other))

        else:
            self.text += other.text

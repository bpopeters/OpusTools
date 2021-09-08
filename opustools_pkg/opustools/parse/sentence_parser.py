import xml.etree.ElementTree as ET


def find_iterparse_groups(lines, tag):
    sentence_buffer = []
    for event, elem in lines:
        if elem.tag == tag and event == "start":
            sentence_buffer = []

        # append to the buffer
        sentence_buffer.append((event, elem))

        if elem.tag == tag and event == "end":
            yield sentence_buffer


class SentenceParser:

    def __init__(
            self, document, preprocessing=None, anno_attrs=('all_attrs',),
            delimiter='|', preserve=None):
        """Parse xml sentence files that have sentence ids in any order.

        Arguments:
        document -- Xml file to be parsed
        preprocessing -- Preprocessing type of the document
        anno_attrs -- Which annotations will be printed
        delimiter -- Annotation attribute delimiter
        preserve -- Preserve inline tags
        """

        self.document = document
        self.delimiter = delimiter
        self.anno_attrs = anno_attrs

        self.preserve = preserve  # do something about this

        self.sentences = {}
        self.done = False

        self.data_tag = "s" if preprocessing == "raw" else "w"

    def store_sentences(self, id_set):
        """
        pre: self.sentences is empty, self.document ready to read
        post: self.sentences is filled with stuff
        """
        sentence_tag = "s"  # may need other things for more advanced cases
        lazy_xml = ET.iterparse(self.document, events=["start", "end"])
        sentences = find_iterparse_groups(lazy_xml, sentence_tag)
        for sent_group in sentences:
            tokens = [elem.text for (event, elem) in sent_group
                      if event == "end" and elem.tag == "w"]
            sentence = ' '.join(tokens)
            sent_attrib = sent_group[-1][1].attrib
            sid = sent_attrib["id"]
            if sid in id_set:
                self.sentences[sid] = sentence, sent_attrib

    def get_annotations(self, block):
        annotations = ''
        if self.anno_attrs[0] == 'all_attrs':
            attributes = list(block.attributes.keys())
            attributes.sort()
            for attr in attributes:
                annotations += self.delimiter + block.attributes[attr]
        else:
            for attr in self.anno_attrs:
                if attr in block.attributes.keys():
                    annotations += self.delimiter + block.attributes[attr]
        return annotations

    def get_sentence(self, sid):
        """Return a sentence based on given sentence id."""
        return self.sentences.get(sid, ('', {}))

    def read_sentence(self, ids):
        """Return a sequence of sentences based on given sentence ids."""
        if len(ids) == 0 or ids[0] == '':
            return '', []

        sentence = []
        attrs_list = []
        for sid in ids:
            new_sentence, attrs = self.get_sentence(sid)
            sentence.append(new_sentence)
            attrs_list.append(attrs)

        return sentence, attrs_list

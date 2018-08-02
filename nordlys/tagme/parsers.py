"""
Query parsers for finding phrases that are not part of wikipedia anchor index.
"""

from spacy.matcher import Matcher
from textacy.extract import noun_chunks, named_entities


#nlp = spacy.load('en')

def get_matcher(pattern_name, patterns, nlp):
    m = Matcher(nlp.vocab)
    for p in patterns:
        m.add(pattern_name, None, p)

    return m


def get_start_end_text_from_span(span):
    start = span.start_char
    end = span.end_char
    mention_txt = span.text
    mention = {"start": start, "end": end, "text": mention_txt}

    return mention


def get_simple_adj_n(nlp):
    pattern = [{'TAG': 'JJ'}, {'POS': 'NOUN'}]
    patterns = [pattern]
    matcher = SpacyPosTagPatternMatcherParser(patterns, nlp, name="simple_adj_n")

    return matcher


def get_compound_n(nlp, more_than_2=False):
    if more_than_2:
        pattern = [{'POS': 'NOUN'}, {'POS': 'NOUN'}, {'POS': 'NOUN', 'OP': '+'}]
        name = "simple_n_n+"
    else:
        pattern = [{'POS': 'NOUN'}, {'POS': 'NOUN'}]
        name = "simple_n_n"
    patterns = [pattern]
    matcher = SpacyPosTagPatternMatcherParser(patterns, nlp, name=name)

    return matcher


def get_textacy_np(nlp, drop_det=True):
    matcher = SpacyBuiltinNpParser(nlp, drop_det=drop_det)

    return matcher


def get_textacy_ner_per_org_gpe_loc(nlp, drop_det=False):
    matcher = SpacyBuiltinNERParser(nlp, drop_det=drop_det, include_types=["PERSON", "ORG", "GPE", "LOC"])

    return matcher


class Parser(object):
    def __init__(self, name):
        self.name = name

    def get_start_end_text(self, text):
        raise NotImplementedError


class SpacyBasedParser(Parser):
    def __init__(self, nlp, name):
        self.nlp = nlp
        self.name = name
        super(SpacyBasedParser, self).__init__(name)

    def get_matching_spans(self, text):
        raise NotImplementedError

    def get_start_end_text(self, text):
        """
        :param text:
        :return:
        """

        spans = self.get_matching_spans(text)
        txt_to_offsets = dict()
        for span in spans:
            info = get_start_end_text_from_span(span)
            if info["text"] not in txt_to_offsets:
                txt_to_offsets[info["text"]] = list()
            txt_to_offsets[info["text"]].append({"start": info["start"],
                                                 "end": info["end"]})

        return txt_to_offsets


class SpacyBuiltinNpParser(SpacyBasedParser):
    def __init__(self, nlp, name="spacy_np", drop_det=True):
        super(SpacyBuiltinNpParser, self).__init__(nlp, name)
        self.drop_det = drop_det

    def get_matching_spans(self, text):
        sdoc = self.nlp(text)
        gen = noun_chunks(sdoc, drop_determiners=self.drop_det)
        matching_spans = [s for s in gen]

        return matching_spans


class SpacyBuiltinNERParser(SpacyBasedParser):
    def __init__(self, nlp, name="spacy_ner", drop_det=False, include_types=None, exclude_types=None):
        super(SpacyBuiltinNERParser, self).__init__(nlp, name)
        self.drop_det = drop_det
        self.include_types=include_types
        self.exclude_types=exclude_types

    def get_matching_spans(self, text):
        sdoc = self.nlp(text)
        gen = named_entities(sdoc, drop_determiners=self.drop_det, include_types=self.include_types,
                             exclude_types=self.exclude_types)
        matching_spans = [s for s in gen]

        return matching_spans


class SpacyPosTagPatternMatcherParser(SpacyBasedParser):
    def __init__(self, patterns, nlp, name):
        """

        :param patters: list of spacy matcher patterns
        """
        super(SpacyPosTagPatternMatcherParser, self).__init__(nlp, name)
        self.patterns = patterns
        self.matcher = get_matcher(pattern_name=self.name, patterns=self.patterns, nlp=self.nlp)

    def get_matching_spans(self, text):
        """
        apply pattern matcher to get spans
        :param text:
        :return:
        """

        sdoc = self.nlp(text)
        matches = self.matcher(sdoc)
        gen = (sdoc[m[1]:m[2]] for m in matches)  # create a span from each match; to match pattern in other
        matching_spans = [s for s in gen]

        return matching_spans
"""
Run this to start service. specify configs in config.yaml in this directory.
"""

from nordlys.tagme.tagme import TagmeQueryProcessor
from nordlys import config
from nordlys.tagme.parsers import *
import spacy
import pprint

tqp = TagmeQueryProcessor()
print("Loaded TQP")


# NOTE: Flask if imported here as part of attempt to figure out how to avoid having to call
from flask import Flask, request, jsonify
app = Flask(__name__, static_url_path='', static_folder='static')


nlp = spacy.load('en')
print("Loaded spaCy")

# list of parsers to find possible element mentions that are not part of TAGME.
# currently separate and there is no attempt to link these mentions.
non_wiki_parsers = [get_simple_adj_n(nlp), get_compound_n(nlp), get_textacy_np(nlp)]
print("Loaded parsers external to tagme")


def add_nonwiki_parser_output(text, parsers, response_dict):
    """
    add phrases spotted by parsers that are not internal to tagme.
    :param response_dict: response dict built by TagmeQueryProcessor
    :return:
    """

    # map each element candidate phrase in the text to a dict mapping parser name to list of offset dictionaries.
    # NOTE: offsets are not currently used.
    text_to_pname_to_offsets = dict()
    for p in parsers:
        txt_to_offsets = p.get_start_end_text(text)
        for mention_txt in txt_to_offsets:
            if mention_txt not in text_to_pname_to_offsets:
                text_to_pname_to_offsets[mention_txt] = dict()

            text_to_pname_to_offsets[mention_txt][p.name] = txt_to_offsets[mention_txt]

    # add mentions to el_cands if they are distinct and non-overlapping with those already picked up by tagme.
    for el_cand_dict in response_dict["el_cands"]:
        txt = el_cand_dict["str"]
        if txt in text_to_pname_to_offsets:
            for parser_name in text_to_pname_to_offsets[txt].keys():
                el_cand_dict["el_extr_mtds"].append({
                    "name": parser_name
                })

    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(text_to_pname_to_offsets)


@app.route('/api/tagme/proc_query/v1', methods=['GET', 'POST'])
def proc_q():
    """
    apply tqp to incoming query
    :return: response object as defined in wiki; element candidatates, their links, and associated scores and metadata.
    """

    # get qa_system
    params = dict((key, value) for key, value in request.json.iteritems())  # TODO if switch to python3 use items()
    query_txt = params["text"]
    res = tqp.process_query(params)
    add_nonwiki_parser_output(query_txt, non_wiki_parsers, res)

    return jsonify(res)


if __name__ == '__main__':
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=False)
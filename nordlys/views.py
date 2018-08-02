"""
Run this to start service. specify configs in config.yaml in this directory.
"""


# TODO weird import order here is artifact of trying to call attachCurrentThread at the right time. Problem still not solved see issue 2404.
from nordlys.tagme.tagme import TagmeQueryProcessor
from nordlys import config
from nordlys.tagme.parsers import Parser


tqp = TagmeQueryProcessor()
print("Loaded TQP")

from nordlys.tagme.parsers import *
import spacy

nlp = spacy.load('en')
non_wiki_parsers = [get_simple_adj_n(nlp)]


def add_nonwiki_parser_output(text, parsers, response_dict):
    # type: (str, list(Parser), dict)
    """
    add phrases spotted by parsers that are not internal to tagme.
    :param response_dict: response dict built by TagmeQueryProcessor
    :return:
    """

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



from flask import Flask, request, jsonify
app = Flask(__name__, static_url_path='', static_folder='static')



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
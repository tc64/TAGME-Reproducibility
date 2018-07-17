"""
Run this to start service. specify configs in config.yaml in this directory.
"""


# TODO weird import order here is artifact of trying to call attachCurrentThread at the right time. Problem still not solved see issue 2404.
from nordlys.tagme.tagme import TagmeQueryProcessor
from nordlys import config

tqp = TagmeQueryProcessor()
print("Loaded TQP")

from nordlys.tagme.parsers import *
import spacy

nlp = spacy.load('en')
non_wiki_parsers = [get_simple_adj_n(nlp)]


def add_nonwiki_parser_output(text, parsers, response_dict):
    """
    add phrases spotted by parsers that are not internal to tagme.
    :param response_dict: response dict built by TagmeQueryProcessor
    :return:
    """

    name_to_mentions = dict()
    for p in parsers:
        info = p.get_start_end_text(text)
        name_to_mentions[p.name] = info

    # add mentions to el_cands if they are distinct and non-overlapping with those already picked up by tagme.
    strs = set()
    for el_cand in response_dict["el_cands"]:


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
    res = tqp.process_query(params)


    return jsonify(res)


if __name__ == '__main__':
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=False)
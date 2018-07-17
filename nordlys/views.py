"""
Run this to start service. specify configs in config.yaml in this directory.
"""

import requests
import json
from flask import Flask, request, jsonify
from os.path import dirname, abspath
from os.path import join
from nordlys.tagme.tagme import TagmeQueryProcessor

tqp = TagmeQueryProcessor()

app = Flask(__name__, static_url_path='', static_folder='static')

#tqp.process_query({"text": "What Is Target Yield For Mexico 10 Year Government Bond By End Of 2018"})

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
    app.run(host='0.0.0.0', port=9002, debug=False)  # TODO configure port number; can put in config.py
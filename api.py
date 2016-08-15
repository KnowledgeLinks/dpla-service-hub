"""REST API for DP.LA Service Hub BIBCAT Aggregator Feed"""
__author__ = "Jeremy Nelson, Mike Stabile"

import click
import json
import xml.etree.ElementTree as etree
import requests
import urllib.parse
from flask import abort, Flask, request, render_template, Response

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')

with open("VERSION") as fo:
    __version__ = fo.read()   

@app.route("/")
def home():
    return "KnowledgeLink.io's DPLA Service Hub Version {}".format(__version__)


@app.route("/oai")
def oai_switcher():
    if 'initiate' in request.args:
        return intermediation(request.args.get('initiate'))
    return abort(500)


def intermediation(static_repo_url):
    """Method takes a Static Repository URL and returns a repository 
    object for use in the OAI-PMH xml template in the format of 
    http://host:port/path/file.

    Args:
       static_repo_url(str): URL for repository
    """
    oai_info = {}
    url_parts = urllib.parse.urlparse(static_repo_url)
    institution_url = "{}://{}/".format(url_parts.scheme, url_parts.netloc)
    oai_info['baseURL'] = institution_url
    sparql_query = """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?name
WHERE {{
<{0}> rdfs:label ?name .
}}""".format(institution_url)
    identify_result = requests.post(
        app.config.get("TRIPLESTORE_URL"),
        data={"query": sparql_query,
              "format":"json"})
    if identify_result.status_code > 300:
        raise Exception("Cannot retrieve {}".format(institution_url))
    bindings = identify_result.json().get('results').get('bindings')
    if len(bindings) < 1:
        return abort(404)
    oai_info['name'] = bindings[0].get('name').get('value')
    return Response(render_template('oai-pmh.xml', repo=oai_info), mimetype="text/xml")
  
    
if __name__ == '__main__':
    app.run(debug=True)

"""REST API for DP.LA Service Hub BIBCAT Aggregator Feed"""
__author__ = "Jeremy Nelson, Mike Stabile"

import click
import datetime
import json
import math
import os
import pkg_resources
import xml.etree.ElementTree as etree
import requests
import rdflib
import urllib.parse

import bibcat.rml.processor as processor

from flask import abort, Flask, jsonify, request, render_template, Response
from flask_cache import Cache
from resync import Resource, ResourceList

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')

PROJECT_BASE =  os.path.abspath(os.path.dirname(__file__))
PREFIX = """PREFIX bf: <http://id.loc.gov/ontologies/bibframe/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX relators: <http://id.loc.gov/vocabulary/relators/>
PREFIX schema: <http://schema.org/>
"""

DPLA_MAPv4 = processor.SPARQLProcessor(
        triplestore_url=app.config.get("TRIPLESTORE_URL"),
        rml_rules=["bf-to-map4.ttl", 
            "{}/profiles/map4.ttl".format(PROJECT_BASE)])

MAPv4_context = {"edm": "http://www.europeana.eu/schemas/edm/",
		 "dcterms": "http://purl.org/dc/terms/",
		 "org": "http://www.openarchives.org/ore/terms"}

__version__ = "0.9.9"

cache = Cache(app, config={"CACHE_TYPE": "filesystem",
                           "CACHE_DIR": os.path.join(PROJECT_BASE, "cache")})


def __run_query__(query):
    """Helper function returns results from sparql query"""
    result = requests.post(app.config.get("TRIPLESTORE_URL"),
        data={"query": query,
              "format": "json"})
    if result.status_code < 400:
        return result.json().get('results').get('bindings')
    


@app.route("/")
def home():
    return render_template("index.html", version=__version__)


@app.route("/<uid>")
def detail(uid):
    """Generates DPLA Map V4 JSON-LD"""
    uri = app.config.get("BASE_URL") + uid
    item_sparql = PREFIX + """
    SELECT DISTINCT ?item
    WHERE {{
        ?item bf:itemOf <{instance_iri}> .
    }}""".format(instance_iri=uri)
    item_results = __run_query__(item_sparql)
    item = item_results[0].get("item").get("value")
    DPLA_MAPv4.run(instance_iri=uri, item_iri=item)
    if len(DPLA_MAPv4.output) < 1:
        abort(404)
    raw_instance = DPLA_MAPv4.output.serialize(
        format='json-ld',
        context=MAPv4_context)
    return Response(raw_instance, mimetype="application/json")
     

@app.route("/siteindex.xml")
#@cache.cached(timeout=86400) # Cached for 1 day
def site_index():
    """Generates siteindex XML, each sitemap has a maximum of 50k links
    dynamically generates the necessary number of sitemaps in the 
    template"""
    bindings = __run_query__(PREFIX + """
SELECT (count(?s) as ?count) WHERE {
   ?s rdf:type bf:Instance .
   ?item bf:itemOf ?s .
}""")
    count = int(bindings[0].get('count').get('value'))
    shards = math.ceil(count/50000)
    mod_date = app.config.get('MOD_DATE')
    if mod_date is None:
        mod_date=datetime.datetime.utcnow().strftime("%Y-%m-%d")
    
    #for row in bindings:
        #resource_list.add(
        #    Resource(
    xml = render_template("siteindex.xml", 
            count=range(1, shards+1), 
            last_modified=mod_date)
    return Response(xml, mimetype="text/xml")

@app.route("/sitemap<offset>.xml", methods=["GET"])
#@cache.cached(timeout=86400)
def sitemap(offset=0):
    offset = (int(offset)*50000) - 50000
    sparql = PREFIX + """

SELECT DISTINCT ?instance ?date
WHERE {{
    ?instance rdf:type bf:Instance .
    ?instance bf:generationProcess ?process .
    ?process bf:generationDate ?date .
    ?item bf:itemOf ?instance .
}} ORDER BY ?instance
LIMIT 50000
OFFSET {0}""".format(offset)
    instances = __run_query__(sparql)
    resource_list = ResourceList()
    for i,row in enumerate(instances):
        instance = row.get('instance')
        last_mod = row.get("date").get("value")[0:10]
        resource_list.add(Resource(instance.get("value"),
                                   lastmod=last_mod))
        if i >= 500:
            xml = resource_list.as_xml()
            break
    #xml = render_template("sitemap_template.xml", instances=instances)
    return Response(xml, mimetype="text/xml")

if __name__ == '__main__':
    app.run(debug=True)

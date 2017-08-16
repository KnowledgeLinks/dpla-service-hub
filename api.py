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

#from dpla_map.feed import generate_maps, Profile
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
        rml_rules=["bf-to-map4.ttl"])

__version__ = "0.9.8"

cache = Cache(app, config={"CACHE_TYPE": "filesystem",
                           "CACHE_DIR": os.path.join(PROJECT_BASE, "cache")})


def __run_query__(query):
    """Helper function returns results from sparql query"""
    result = requests.post(app.config.get("TRIPLESTORE_URL"),
        data={"query": query,
              "format": "json"})
    if result.status_code < 400:
        print(result.json().keys())
        return result.json().get('results').get('bindings')
    


@app.route("/")
def home():
    return render_template("index.html", version=__version__)


@app.route("/map/v4")
def map():
    return "In generate MAPv4 route"

@app.route("/<uid>")
def detail(uid):
    """Generates DPLA Map V4 JSON-LD"""
    uri = app.config.get("BASE_URL") + uid
    DPLA_MAPv4.run(instance_iri=uri)
    if len(DPLA_MAPv4.output) < 1:
        abort(404)
    raw_instance = DPLA_MAPv4.output.serialize(format='json-ld')
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
    sparql_query = """prefix bf: <http://id.loc.gov/ontologies/bibframe/>
SELECT DISTINCT ?instance ?mtitle
WHERE {{
?instance rdf:type bf:Instance .
?instance bf:title ?title .
?title bf:mainTitle ?mtitle
}} LIMIT 100"""
    instance_result = requests.post(
        app.config.get("TRIPLESTORE_URL"),
        data={"query": sparql_query,
              "format": "json"})
    if instance_result.status_code > 300:
        raise Exception("Error with getting Instances")
    oai_info['instances'] = []
    bindings = instance_result.json().get('results').get('bindings')
    for row in bindings:
        oai_info['instances'].append({"name": row.get('mtitle').get('value'),
                                      "uri": row.get('instance').get('value')})
    return Response(render_template('oai-pmh.xml', repo=oai_info), mimetype="text/xml")
    
if __name__ == '__main__':
    app.run(debug=True)

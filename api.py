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

import reports
import bibcat.rml.processor as processor

from zipfile import ZipFile, ZIP_DEFLATED

from flask import abort, Flask, jsonify, request, render_template, Response
from flask import flash, url_for
from flask import flash

from flask_cache import Cache
from resync import CapabilityList, ResourceDump, ResourceDumpManifest
from resync import ResourceList
from resync.resource import Resource
from resync.resource_list import ResourceListDupeError
from resync.dump import Dump

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')

BF = rdflib.Namespace("http://id.loc.gov/ontologies/bibframe/")

PROJECT_BASE =  os.path.abspath(os.path.dirname(__file__))
PREFIX = """PREFIX bf: <http://id.loc.gov/ontologies/bibframe/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX relators: <http://id.loc.gov/vocabulary/relators/>
PREFIX schema: <http://schema.org/>
"""

DPLA_MAPv4 = processor.SPARQLBatchProcessor(
        triplestore_url=app.config.get("TRIPLESTORE_URL"),
        rml_rules=["bf-to-map4.ttl",
            "{}/profiles/map4.ttl".format(PROJECT_BASE)])

MAPv4_context = {"edm": "http://www.europeana.eu/schemas/edm/",
		 "dcterm": "http://purl.org/dc/terms/",
		 "org": "http://www.openarchives.org/ore/terms"}

W3C_DATE = "%Y-%m-%dT%H:%M:%SZ"

__version__ = "0.9.12"

cache = Cache(app, config={"CACHE_TYPE": "filesystem",
                           "CACHE_DIR": os.path.join(PROJECT_BASE, "cache")})


def __run_query__(query):
    """Helper function returns results from sparql query"""
    result = requests.post(app.config.get("TRIPLESTORE_URL"),
        data={"query": query,
              "format": "json"})
    if result.status_code < 400:
        return result.json().get('results').get('bindings')

def __get_instances__(offset=0):
    """Helper function used by siteindex and resourcedump views

    Args:
        offset(int): offset number of records
    """
    offset = int(offset)*50000
    sparql = PREFIX + """

SELECT DISTINCT ?instance ?date
WHERE {{
    ?instance rdf:type bf:Instance .
    OPTIONAL {{
        ?instance bf:generationProcess ?process .
        ?process bf:generationDate ?date .
    }}
}} ORDER BY ?instance
LIMIT 50000
OFFSET {0}""".format(offset)
    instances = __run_query__(sparql)
    return instances


def __get_mod_date__(entity_iri=None):
    if "MOD_DATE" in app.config:
        return app.config.get("MOD_DATE")
    return datetime.datetime.utcnow().strftime(W3C_DATE)



def __generate_profile__(instance_uri):
    item_sparql = PREFIX + """
    SELECT DISTINCT ?item
    WHERE {{
        ?item bf:itemOf <{instance_iri}> .
    }}""".format(instance_iri=instance_uri)
    item_results = __run_query__(item_sparql)
    if len(item_results) < 1:
        abort(404)
    item = item_results[0].get("item").get("value")
    DPLA_MAPv4.run(instance_iri=instance_uri,
                   item_iri=item)
    if len(DPLA_MAPv4.output) < 1:
        abort(404)
    raw_instance = DPLA_MAPv4.output.serialize(
        format='json-ld',
        context=MAPv4_context)
    if isinstance(raw_instance, bytes):
        raw_instance = raw_instance.decode()
    instance = json.loads(raw_instance)
    # Post-processing to change certain properties to be
    # a Python list instead of a single literal or URI
    json_array_fields = ["dcterm:title",
                         "dcterm:alternative",
                         "dcterm:identifier",
                         "dc:date",
                         "dcterm:language",
                         "dcterm:creator",
                         "dcterm:extent",
                         "dcterm:subject"]
    for entity in instance.get('@graph'):
        for field in json_array_fields:
            if field in entity and not isinstance(entity.get(field), list):
                org_value = entity.get(field)
                entity[field] = [org_value,]

    return json.dumps(instance)


def __generate_resource_dump__():
    r_dump = ResourceDump()
    r_dump.ln.append({"rel": "resourcesync",
                      "href": url_for('capability_list')})

    bindings = __run_query__(PREFIX + """
SELECT (count(?s) as ?count) WHERE {
   ?s rdf:type bf:Instance .
   ?item bf:itemOf ?s .
}""")
    count = int(bindings[0].get('count').get('value'))
    shards = math.ceil(count/50000)
    for i in range(0, shards):
        zip_info = __generate_zip_file__(i)
        r_dump.add(
            Resource(url_for('resource_zip',
                             offset=i*50000),
                     lastmod=zip_info.get('date'),
                     type="application/zip",
                     length=zip_info.get("size")
            )
        )
    return r_dump

def __generate_zip_file__(offset=0):
    start = datetime.datetime.utcnow()
    print("Started at {}".format(start.ctime()))
    manifest = ResourceDumpManifest()
    manifest.modified = datetime.datetime.utcnow().isoformat()
    manifest.ln.append({"rel": "resourcesync",
                        "href": url_for('capability_list')})
    file_name = "{}-{:03}.zip".format(
                               datetime.datetime.utcnow().toordinal(),
                               offset)
    tmp_location = os.path.join(PROJECT_BASE,
                                "dump/{}".format(file_name))
    if os.path.exists(tmp_location) is True:
        return {"date": os.path.getmtime(tmp_location),
                "size": os.path.getsize(tmp_location)}
    dump_zip = ZipFile(tmp_location,
                       mode="w",
                       compression=ZIP_DEFLATED,
                       allowZip64=True)
    instances = __get_instances__(offset)
    for i,row in enumerate(instances):
        instance_iri = row.get("instance").get('value')
        key = instance_iri.split("/")[-1]
        if not "date" in row:
            last_mod = __get_mod_date__()
        else:
            last_mod = "{}Z".format(row.get("date").get("value"))
        path = "/resources/{}.json".format(key)
        raw_json = __generate_profile__(instance_iri)
        dump_zip.writestr(path,
                          raw_json)
        manifest.add(
            Resource(instance_iri,
                     lastmod=last_mod,
                     length="{}".format(len(raw_json)),
                     path=path))
        if not i%25 and i > 0:
            print(".", end="")
        if not i%100:
            print("{:,}".format(i), end="")
    dump_zip.writestr("manifest.xml", manifest.as_xml())
    dump_zip.close()
    end = datetime.datetime.utcnow()
    print("Finished at {}, total time {} min, size={}".format(
        end.ctime(),
        (end-start).seconds / 60.0,
        i))
    return {"date": datetime.datetime.utcnow().isoformat(),
            "size": len(dump_zip)}

@app.template_filter("pretty_num")
def nice_number(raw_number):
    if raw_number is None:
        return ''
    return "{:,}".format(int(raw_number))

@app.route("/")
def home():
    """Default page"""
    result = __run_query__("SELECT (COUNT(*) as ?count) WHERE {?s ?p ?o }")
    count = result[0].get("count").get("value")
    if int(count) < 1:
        flash("Triplestore is empty, please load service hub RDF data")
    return render_template("index.html",
        version=__version__,
        count="{:,}".format(int(count)))

@app.route("/reports/")
@app.route("/reports/<path:name>")
def reporting(name=None):
    if name is None:
        return render_template("reports/index.html")
    report_output = reports.report_router(name)
    if report_output is None:
        abort(404)
    return render_template(
        "reports/{0}.html".format(name),
        data=report_output)


@app.route("/<path:type_of>/<path:name>")
def authority_view(type_of, name=None):
    """Generates a RDF:Description view for Service Hub name,
    topic, agent, and other types of BIBFRAME entities

    Args:
        type_of(str): Type of entity
        name(str): slug of name, title, or other textual identifier
    """
    if name is None:
        # Display brows view of authorities
        return "Browse display for {}".format(type_of)
    uri = "{0}{1}/{2}".format(app.config.get("BASE_URL"),
        type_of,
        name)
    entity_sparql = PREFIX + """
    SELECT DISTINCT ?label ?value
    WHERE {{
        <{entity}> rdf:type {type_of} .
        OPTIONAL {{
            <{entity}> rdfs:label ?label
        }}
        OPTIONAL {{
            <{entity}> rdf:value ?value
        }}
    }}""".format(entity=uri,
        type_of="bf:{}".format(type_of.title()))
    entity_results = __run_query__(entity_sparql)
    if len(entity_results) < 1:
        abort(404)
    entity_graph = rdflib.Graph()
    iri = rdflib.URIRef(uri)
    entity_graph.add((iri, rdflib.RDF.type, getattr(BF, type_of.title())))
    for row in entity_results:
        if 'label' in row:
            literal = rdflib.Literal(row.get('label').get('value'),
                                     datatype=row.get('label').get('datatype'))

            entity_graph.add((iri, rdflib.RDFS.label, literal))
        if 'value' in row:
            literal = rdflib.Literal(row.get('value').get('value'),
                                    datatype=row.get('value').get('datatype'))
            entity_graph.add((iri, rdflib.RDF.value, literal))
    MAPv4_context["bf"] = str(BF)
    raw_entity = entity_graph.serialize(format='json-ld',
        context=MAPv4_context)
    return Response(raw_entity, mimetype="application/json")

@app.route("/capabilitylist.xml")
def capability_list():
    cap_list = CapabilityList()
    cap_list.modified = __get_mod_date__()
    cap_list.ln.append({"href": url_for('capability_list'),
                        "rel": "describedby",
                        "type": "application/xml"})
    cap_list.add(Resource(url_for('site_index'),
                          capability="resourcelist"))
    cap_list.add(Resource(url_for('resource_dump'),
                          capability="resourcedump"))
    return Response(cap_list.as_xml(),
                    mimetype="text/xml")


@app.route("/resourcedump.xml")
def resource_dump():
    xml = __generate_resource_dump__()
    return Response(xml,
            "text/xml")

@app.route("/resourcedump-<int:count>.zip")
def resource_zip(count):
    zip_location = os.path.join(PROJECT_BASE,
        "dump/{}.zip".format(count))
    if not os.path.exists(zip_location):
        abort(404)
    return send_file(zip_location)

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
    xml = render_template("siteindex.xml",
            count=range(1, shards+1),
            last_modified=mod_date)
    return Response(xml, mimetype="text/xml")

@app.route("/sitemap<int:offset>.xml", methods=["GET"])
#@cache.cached(timeout=86400)
def sitemap(offset=0):
    if offset > 0:
        offset = offset - 1
    instances = __get_instances__(offset)
    resource_list = ResourceList()
    dedups = 0
    for i,row in enumerate(instances):
        instance = row.get('instance')
        if "date" in row:
            last_mod = row.get("date").get("value")[0:10]
        else:
            last_mod = datetime.datetime.utcnow().strftime(
                W3C_DATE)
        try:
            resource_list.add(
                Resource("{}.json".format(instance.get("value")),
                         lastmod=last_mod)
            )
        except ResourceListDupeError:
            dedups += 1
            continue
    xml = resource_list.as_xml()
    return Response(xml, mimetype="text/xml")

@app.route("/<uid>.json")
def detail(uid=None):
    """Generates DPLA Map V4 JSON-LD"""
    if uid.startswith('favicon'):
        return ''
    if uid is None:
        abort(404)
    uri = app.config.get("BASE_URL") + uid
    raw_instance = __generate_profile__(uri)
    return Response(raw_instance, mimetype="application/json")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

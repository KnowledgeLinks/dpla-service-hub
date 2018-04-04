"""REST API for DP.LA Service Hub BIBCAT Aggregator Feed"""
__author__ = "Jeremy Nelson, Mike Stabile"

import click
import datetime
import hashlib
import json
import math
import os
import pkg_resources
import xml.etree.ElementTree as etree
import requests
import rdflib
import sys
import urllib.parse

import reports
import bibcat.rml.processor as processor

from zipfile import ZipFile, ZIP_DEFLATED

from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Search, Q

from flask import abort, Flask, jsonify, request, render_template, Response
from flask import flash, url_for
from flask import flash
#from flask_cache import Cache

from resync import CapabilityList, ResourceDump, ResourceDumpManifest
from resync import ResourceList
from resync.resource import Resource
from resync.resource_list import ResourceListDupeError
from resync.dump import Dump

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')

from rdfframework.rml import RmlManager
from rdfframework.configuration import RdfConfigManager
from rdfframework.datamanager import DefinitionManager
from rdfframework.datatypes import RdfNsManager

RmlManager().register_defs([('package_all', 'bibcat.maps')])
# Define vocabulary and definition file locations
DefinitionManager().add_file_locations([('vocabularies', ['rdf',
                                                          'rdfs',
                                                          'owl',
                                                          'schema',
                                                          'bf',
                                                          'skos',
                                                          'dcterm']),
                                        ('package_all',
                                         'bibcat.rdfw-definitions')])
# Register RDF namespaces to use
RdfNsManager({'acl': '<http://www.w3.org/ns/auth/acl#>',
              'bd': '<http://www.bigdata.com/rdf#>',
              'bf': 'http://id.loc.gov/ontologies/bibframe/',
              'dbo': 'http://dbpedia.org/ontology/',
              'dbp': 'http://dbpedia.org/property/',
              'dbr': 'http://dbpedia.org/resource/',
              'dc': 'http://purl.org/dc/elements/1.1/',
              'dcterm': 'http://purl.org/dc/terms/',
              'dpla': 'http://dp.la/about/map/',
              'edm': 'http://www.europeana.eu/schemas/edm/',
              'es': 'http://knowledgelinks.io/ns/elasticsearch/',
              'foaf': 'http://xmlns.com/foaf/0.1/',
              'loc': 'http://id.loc.gov/authorities/',
              'm21': '<http://knowledgelinks.io/ns/marc21/>',
              'mads': '<http://www.loc.gov/mads/rdf/v1#>',
              'mods': 'http://www.loc.gov/mods/v3#',
              'ore': 'http://www.openarchives.org/ore/terms/',
              'owl': 'http://www.w3.org/2002/07/owl#',
              'relators': 'http://id.loc.gov/vocabulary/relators/',
              'schema': 'http://schema.org/',
              'skos': 'http://www.w3.org/2004/02/skos/core#',
              'xsd': 'http://www.w3.org/2001/XMLSchema#'})

CONFIG_MANAGER = RdfConfigManager(app.config, verify=False)
CONNECTIONS = CONFIG_MANAGER.conns

BF = rdflib.Namespace("http://id.loc.gov/ontologies/bibframe/")

W3C_DATE = "%Y-%m-%dT%H:%M:%SZ"

__version__ = "1.0.0"

#cache = Cache(app, config={"CACHE_TYPE": "filesystem",
#                           "CACHE_DIR": os.path.join(PROJECT_BASE, "cache")})


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
    sparql = """
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
    instances = CONNECTIONS.datastore.query(sparql) 
    return instances


def __get_mod_date__(entity_iri=None):
    if "MOD_DATE" in app.config:
        return app.config.get("MOD_DATE")
    return datetime.datetime.utcnow().strftime(W3C_DATE)



def __generate_profile__(instance_uri):
    work_iri = "{}#Work".format(instance_uri)
    work_sha1 = hashlib.sha1(work_iri.encode())
    click.echo("Work sha1 {}".format(work_sha1.hexdigest()))
    try:
        click.echo("Before call to search")
        work_result = CONNECTIONS.search.es.get(
            "works_v1",
            work_sha1.hexdigest(),
            _source=["bf_hasInstance.bf_hasItem.rml_map.map4_json_ld"])
        click.echo("After es call")
    except NotFoundError:
        click.echo("Connection NotFoundError from ES")
        return
    except:
        click.echo("Raised error {}".format(sys.exc_info()))
        return 
    if  work_result is None:
        click.echo("Work result is None")
        #abort(404)
        #click.echo("{}#Work missing _source".format(instance_uri))
        return
    click.echo("Work result {}".format(work_result.keys()))
    return work_result.get("_source").get("bf_hasInstance", [])[0].\
           get("bf_hasItem", [])[0].get("rml_map", {}).get("map4_json_ld")


def __generate_resource_dump__():
    r_dump = ResourceDump()
    r_dump.ln.append({"rel": "resourcesync",
                      "href": url_for('capability_list')})

    bindings = CONNECTIONS.datastore.query("""
SELECT (count(?s) as ?count) WHERE {
   ?s rdf:type bf:Instance .
   ?item bf:itemOf ?s .
}""")
    count = int(bindings[0].get('count').get('value'))
    shards = math.ceil(count/50000)
    for i in range(0, shards):
        zip_info = __generate_zip_file__(i)
        try:
            zip_modified = datetime.datetime.fromtimestamp(zip_info.get('date'))
            last_mod = zip_modified.strftime("%Y-%m-%d")

        except TypeError:
            last_mod = zip_info.get('date')[0:10]
        click.echo("Total errors {:,}".format(
            len(zip_info.get('errors', []))))
        r_dump.add(
            Resource(url_for('resource_zip',
                             count=i*50000),
                     lastmod=last_mod,
                     mime_type="application/zip",
                     length=zip_info.get("size")
            )
        )
    return r_dump

def __generate_zip_file__(offset=0):
    start = datetime.datetime.utcnow()
    click.echo("Started at {}".format(start.ctime()))
    manifest = ResourceDumpManifest()
    manifest.modified = datetime.datetime.utcnow().isoformat()
    manifest.ln.append({"rel": "resourcesync",
                        "href": url_for('capability_list')})
    file_name = "{}-{:03}.zip".format(
                               datetime.datetime.utcnow().toordinal(),
                               offset)
    
    tmp_location = os.path.join(app.config.get("DIRECTORIES")[0].get("path"),
                                "dump/{}".format(file_name))
    if os.path.exists(tmp_location) is True:
        return {"date": os.path.getmtime(tmp_location),
                "size": os.path.getsize(tmp_location)}
    dump_zip = ZipFile(tmp_location,
                       mode="w",
                       compression=ZIP_DEFLATED,
                       allowZip64=True)
    instances = __get_instances__(offset)
    errors = []
    click.echo("Iterating through {:,} instances".format(len(instances)))
    for i,row in enumerate(instances):
        instance_iri = row.get("instance").get('value')
        key = instance_iri.split("/")[-1]
        if not "date" in row:
            last_mod = __get_mod_date__()
        else:
            last_mod = "{}".format(row.get("date").get("value")[0:10])
        path = "resources/{}.json".format(key)
        if not i%25 and i > 0:
            click.echo(".", nl=False)
        if not i%100:
            click.echo("{:,}".format(i), nl=False)
        raw_json = __generate_profile__(instance_iri)
        if raw_json is None:
            errors.append(instance_iri)
            continue
        elif len(raw_json) < 1:
            click.echo(instance_iri, nl=False)
            break
        dump_zip.writestr(path,
                          raw_json)
        manifest.add(
            Resource(instance_iri,
                     lastmod=last_mod,
                     length="{}".format(len(raw_json)),
                     path=path))
    dump_zip.writestr("manifest.xml", manifest.as_xml())
    dump_zip.close()
    end = datetime.datetime.utcnow()
    zip_size = os.stat(tmp_location).st_size
    click.echo("Finished at {}, total time {} min, size={}".format(
        end.ctime(),
        (end-start).seconds / 60.0,
        i))
    return {"date": datetime.datetime.utcnow().isoformat(),
            "size": zip_size,
            "errors": errors}

@app.template_filter("pretty_num")
def nice_number(raw_number):
    if raw_number is None:
        return ''
    return "{:,}".format(int(raw_number))

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", error=e), 404

@app.route("/")
def home():
    """Default page"""
    result = CONNECTIONS.datastore.query(
        "SELECT (COUNT(*) as ?count) WHERE {?s ?p ?o }")
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
    return Response(xml.as_xml(),
            mimetype="text/xml")

@app.route("/resourcedump-<int:count>.zip")
def resource_zip(count):
    zip_location = os.path.join(app.config.get("DIRECTORIES")[0].get("path"),
                                "dump/resour{}".format(file_name))
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
    result = CONNECTIONS.datastore.query("""SELECT (count(?work) as ?count)
WHERE {
    ?work rdf:type bf:Work .
    ?instance bf:instanceOf ?work .
    ?item bf:itemOf ?instance . }""")
    count = int(result[0].get('count').get('value'))
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

@app.route("/<path:uid>.json")
def detail(uid=None):
    """Generates DPLA Map V4 JSON-LD"""
    if uid.startswith('favicon'):
        return ''
    click.echo("UID is {}".format(uid))
    if uid is None:
        abort(404)
    uri = app.config.get("BASE_URL") + uid
    click.echo("URI is {}".format(uri))
    raw_map_4 = __generate_profile__(uri)
    click.echo("After generate profile {}".format(raw_map_4))
    return Response(raw_map_4, mimetype="application/json")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

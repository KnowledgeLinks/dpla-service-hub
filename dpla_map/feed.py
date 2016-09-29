"""Module provides a JSON MAPv4 feed for ingestion by DP.LA"""
__author__ = "Jeremy Nelson, Mike Stabile"

import json
import rdflib
import requests
import uuid

from .map_sparql import GET_ENTITIES

from flask import Response
from bibcat.ingesters.ingester import new_graph 
from rdfw.rdfframework.utilities.uriconvertor import RdfNsManager

NS_MGR = RdfNsManager()


class Profile(object):
    """Profile will generate a DPLA Profile for a BIBFRAME 2.0 BF Instance 
    or Item"""

    def __init__(self, **kwargs):
        self.rules = new_graph()
        self.sparql_endpoint = kwargs.get("sparql",
            "http://localhost:9999/blazegraph/sparql")
        self.base_url = kwargs.get('base_url')
        if self.base_url is None and hasattr(app.config, "BASE_URL"):
            self.base_url = app.config.BASE_URL
        else:
            self.base_url = "http://bibcat.org/"

    def __generate_uri__(self):
        """Method generates an URI based on the base_url"""
        uid = uuid.uuid1()
        if self.base_url.endswith("/"):
            pattern = "{0}{1}"
        else:
            pattern = "{0}/{1}"
        return rdflib.URIRef(pattern.format(self.base_url, uid))

    def __source_resource__(self, entity_iri, graph):
        """Takes an entity IRI and graph, queries triplestore based on the 
        rules, adds to graph, and returns the new Source Resource IRI

        Args:
            entity_iri(rdflib.URIRef): Entity IRI
            graph(rdflib.Graph): Output Graph
        """
        source_resource_iri = self.__generate_uri__()
        graph.add((source_resource_iri, 
                   NS_MGR.rdf.type, 
                   NS_MGR.dpla.SourceResource))
        return source_resource_iri


    def generate(self, entity_uri):
        graph = new_graph()
        if isinstance(entity_uri, rdflib.URIRef):
            entity_iri = entity_uri
        else:
            entity_iri = rdflib.URIRef(entity_uri)
        source_resource = self.__source_resource__(entity_iri, graph)

        return graph

    

def generate_maps(offset=0):
    """Generates a DPLA Metadata Application Profile JSON-LD feed"""
    profile = Profile()
    def generate(offset):
        result = requests.post(app.config.get("TRIPLESTORE_URL"),
                        data={"query": GET_ENTITIES.format(
                                           NS_MGR.bf.Item,
                                           offset),
                              "format": "json"})
        if not result.status_code < 400:
            bindings = []
        else:
            bindings = result.json().get('results').get('bindings')
        for row in bindings:
            graph = profile.generate(row.get('entity_uri').get('value'))
            yield graph.serialize(format='json-ld')
    return Response(generate(offset), mimetype='application/json')

from api import app

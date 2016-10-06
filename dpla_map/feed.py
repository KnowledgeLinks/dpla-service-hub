"""Module provides a JSON MAPv4 feed for ingestion by DP.LA"""
__author__ = "Jeremy Nelson, Mike Stabile"

import json
import os
import rdflib
import requests
import uuid

from .map_sparql import GET_ENTITY_INFO, GET_ENTITIES, GET_RULES

from flask import Response
from bibcat.ingesters.ingester import new_graph 
from rdfw.rdfframework.utilities.uriconvertor import RdfNsManager

PROJECT_BASE = os.path.abspath(
    os.path.split(
        os.path.dirname(__file__))[0])


class Profile(object):
    """Profile will generate a DPLA Profile for a BIBFRAME 2.0 BF Instance 
    or Item"""

    def __init__(self, **kwargs):
        self.rules = new_graph()
        self.rules.parse(os.path.join(PROJECT_BASE, 'custom/bf-dpla-map.ttl'),
            format='turtle')
        self.sparql_endpoint = kwargs.get("sparql",
            "http://localhost:9999/blazegraph/sparql")
        self.base_url = kwargs.get('base_url')
        if self.base_url is None and hasattr(config, "BASE_URL"):
            self.base_url = config.BASE_URL
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

    def __aggregation__(self, entity_iri, graph):
        """Takes an entity IRI and graph, queries triplestore based on the 
        rules, adds to graph, and returns the new Aggregation IRI

        Args:
            entity_iri(rdflib.URIRef): Entity IRI
            graph(rdflib.Graph): Output Graph
        """
        aggregation_iri = self.__generate_uri__()
        graph.add((aggregation_iri, NS_MGR.rdf.type, NS_MGR.ore.Aggregation))
        sparql = GET_RULES.format(NS_MGR.ore.Aggregation)
        for row in self.rules.query(sparql):
            destPropUri, linkedRange, linkedClass = row
            if isinstance(linkedRange, rdflib.BNode):
                continue
            self.__populate__(entity=aggregation_iri,
                              graph=graph,
                              linkedRange=linkedRange,
                              linkedClass=linkedClass)

        return aggregation_iri

    def __populate__(self, **kwargs):
        entity_iri = kwargs.get('entity')
        graph = kwargs.get('graph')
        linked_range = kwargs.get('linkedRange')
        linked_class = kwargs.get('linkedClass')
        dest_prop_uri = kwargs.get("destPropUri")
        linked_sparql = GET_ENTITY_INFO.format(entity_iri, 
                                               linked_range)
        rule_result = requests.post(self.sparql_endpoint,
            data={"query": linked_sparql,
                   "format": "json"})
        bindings = rule_result.json().get('results').get('bindings')
        for row in bindings:
            if row.get('type').startswith("ur"):
                obj_ = rdflib.URIRef(row.get('value'))
            elif row.get('type').startswith('literal'):
                obj_ = rdflib.Literal(row.get('value'))
            graph.add((entity_iri, 
                       dest_prop_uri, 
                       obj_))       

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

    def __web_resource__(self, entity_iri, graph):
        """Takes an entity IRI and graph, queries triplestore based on the 
        rules, adds to graph the properties with the new entity IRI as a
        edm:WebResource

        Args:
            entity_iri(rdflib.URIRef): Entity IRI
            graph(rdflib.Graph): Output Graph
        """
        graph.add((entity_iri, NS_MGR.rdf.type, NS_MGR.edm.WebResource))
        

    

    def generate(self, entity_uri):
        """Takes an entity URI and generates a DPLA JSON-LD Profile RDF graph. 

        Args:
            entity_uri(str|URIRef): Entity URI

        Returns:
            rdflib.ConjectiveGraph
        """
        graph = new_graph()
        if isinstance(entity_uri, rdflib.URIRef):
            entity_iri = entity_uri
        else:
            entity_iri = rdflib.URIRef(entity_uri)
        source_resource = self.__source_resource__(entity_iri, graph)
        aggregation_iri = self.__aggregation__(entity_iri, graph)
        graph.add((aggregation_iri, 
                   NS_MGR.edm.aggregatedCHO, source_resource))
        graph.add((aggregation_iri,
                   NS_MGR.edm.hasView,
                   entity_iri))
        self.__web_resource__(entity_iri, graph)
        return graph

    

def generate_maps():
    """Generates a DPLA Metadata Application Profile JSON-LD feed"""
    profile = Profile()
    def generate():
        sparql = GET_ENTITIES.format(NS_MGR.bf.Item, 0)
        result = requests.post(config.TRIPLESTORE_URL,
                        data={"query": sparql,
                              "format": "json"})
        if not result.status_code < 400:
            bindings = []
        else:
            bindings = result.json().get('results').get('bindings')
        for row in bindings:
            graph = profile.generate(row.get('entity_iri').get('value'))
            yield graph.serialize(format='json-ld')
    return Response(generate(), mimetype='application/json')

from instance import config
NS_MGR = RdfNsManager(config=config)

"""Module provides a JSON MAPv4 feed for ingestion by DP.LA"""
__author__ = "Jeremy Nelson, Mike Stabile"

import json
import os
import rdflib
import requests
import uuid

from .map_sparql import GET_ENTITY_INFO, GET_ENTITIES, GET_RULES
from .map_sparql import GET_BNODE_INFO, GET_PUBLISHER, WEB_RESOURCE

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

    def __guess_type__(self, entity_iri, graph):
        sparql = GET_TYPES.format(entity_iri)
        results = requests.post(self.sparql_endpoint,
            data={"query": sparql,
                  "format": "json"})
        bindings = results.json().get('results').get('bindings')
        for row in bindings:
            bf_class = rdflib.URIRef(row.get('type_of').get('value'))
            if bf_class == NS_MGR.bf.Image:
                dcmi_type = NS_MGR.dcmitype.Image
            elif bf_class == NS_MGR.bf.Audio:
                dcmi_type = NS_MGR.dcmitype.Sound
            elif bf_class == NS_MGR.MovingImage:
                dcmi_type = NS_MGR.dcmitype.MovingImage
            else: # Default Type
                dcmi_type = NS_MGR.dcmitype.Text
            graph.add((entity_iri, NS_MGR.dc.type, dcmi_type))
            


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
            type_of = row.get('value').get('type')
            if type_of.startswith("ur"):
                obj_ = rdflib.URIRef(row.get('value').get('value'))
            elif type_of.startswith('literal'):
                obj_ = rdflib.Literal(row.get('value').get('value'))
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
        graph.add((entity_iri, 
                   NS_MGR.rdf.type, 
                   NS_MGR.dpla.SourceResource))
        sparql = GET_RULES.format(NS_MGR.dpla.SourceResource)
        for row in self.rules.query(sparql):
            destPropUri, linkedRange, linkedClass = row
            if isinstance(linkedRange, rdflib.BNode):
                bnode_range = self.rules.value(subject=linkedRange,
                                               predicate=NS_MGR.rdf.type)
                bnode_prop = self.rules.value(subject=linkedRange,
                                              predicate=NS_MGR.kds.linkedRange)
                sparql = GET_BNODE_INFO.format(entity_iri, 
                    bnode_range, 
                    bnode_prop)
                bnode_result = requests.post(self.sparql_endpoint,
                    data={"query": sparql,
                          "format": "json"})
                bindings = bnode_result.json().get("results").get("bindings")
                for row in bindings:
                    type_of = row.get("value").get("type")
                    if type_of.startswith("ur"):
                        obj_ = rdflib.URIRef(row.get('value').get('value'))
                    elif type_of.startswith("literal"):
                        obj_ = rdflib.Literal(row.get('value').get('value'))
                    graph.add((entity_iri, destPropUri, obj_))
                continue
            self.__populate__(entity=entity_iri,
                              graph=graph,
                              destPropUri=destPropUri,
                              linkedRange=linkedRange,
                              linkedClass=linkedClass)
        # Direct query for Publisher info
        sparql = GET_PUBLISHER.format(entity_iri)
        publisher_result = requests.post(self.sparql_endpoint,
            data={"query": sparql,
                  "format": "json"})
        bindings = publisher_result.json().get("results").get("bindings")
        if len(bindings) > 0:
            raw_label = bindings[0].get("label").get("value")
            if len(raw_label) > 0:
                graph.add((entity_iri,
                           NS_MGR.dc.publisher, 
                           rdflib.Literal(raw_label)))
        return entity_iri

    def __web_resource__(self, entity_iri, graph):
        """Takes an entity IRI and graph, queries triplestore based on the 
        rules, adds to graph the properties with the new entity IRI as a
        edm:WebResource

        Args:
            entity_iri(rdflib.URIRef): Entity IRI
            graph(rdflib.Graph): Output Graph
        """
        sparql = WEB_RESOURCE.format(entity_iri)
        result = requests.post(self.sparql_endpoint,
            data={"query": sparql,
                  "format": "json"})
        bindings = result.json().get('results').get('bindings')
        item_iri = rdflib.URIRef(bindings[0].get('item').get('value'))
        graph.add((item_iri, NS_MGR.rdf.type, NS_MGR.edm.WebResource))
        sparql = GET_RULES.format(NS_MGR.edm.WebResource)
        for row in self.rules.query(sparql):
            destPropUri, linkedRange, linkedClass = row
            self.__populate__(entity=item_iri,
                              graph=graph,
                              destPropUri=destPropUri,
                              linkedRange=linkedRange,
                              linkedClass=linkedClass)


        

    

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

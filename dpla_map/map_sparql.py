"""Contains SPARQL templates for creating DPLA MAPv4 from BIBFRAME 2.0 RDF"""
__author__ = "Jeremy Nelson, Mike Stabile"

from bibcat.ingesters.ingester import NS_MGR

PREFIX = NS_MGR.prefix()

GET_ENTITIES = PREFIX + """
SELECT DISTINCT entity_iri 
WHERE {{
    entity_iri rdf:type bf:Item

}} LIMIT 1000 OFFSET {0}"""

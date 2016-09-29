"""Contains SPARQL templates for creating DPLA MAPv4 from BIBFRAME 2.0 RDF"""
__author__ = "Jeremy Nelson, Mike Stabile"

from bibcat.ingesters.ingester import NS_MGR

PREFIX = NS_MGR.prefix()

GET_ENTITY_INFO = PREFIX + """
SELECT ?value
WHERE {{
    <{0}> <{1}> ?prop .
    OPTIONAL {{ ?prop rdf:value ?value }}
    OPTIONAL {{ ?prop rdfs:label ?value }}
}}"""

GET_ENTITIES = PREFIX + """
SELECT DISTINCT ?entity_iri 
WHERE {{
    ?entity_iri rdf:type <{0}>

}} LIMIT 100 OFFSET {1}"""

GET_RULES = PREFIX + """
SELECT ?destPropUri ?linkedRange ?linkedClass
WHERE {{
    ?rule rdf:type kds:PropertyExport .
    ?rule kds:destClassUri <{0}> .
    ?rule kds:destPropUri ?destPropUri .
    ?rule kds:linkedRange ?linkedRange .
    ?rule kds:linkedClass ?linkedClass .
}}"""


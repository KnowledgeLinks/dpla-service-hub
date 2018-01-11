__author__ = "Jeremy Nelson"

from instance import config
from collections import OrderedDict
import requests

PREFIX = """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX bf: <http://id.loc.gov/ontologies/bibframe/>
PREFIX schema: <http://schema.org/>
"""

INSTITUTIONS = OrderedDict()

def __init_institutions__():
    global INSTITUTIONS
    INSTITUTIONS_SPARQL = PREFIX + """
SELECT DISTINCT ?institution ?label 
WHERE {
    ?institution rdf:type ?type ;
        rdfs:label ?label .
    FILTER(?type=schema:Library||?type=schema:Museum||?type=schema:CollegeOrUniversity||?type=schema:Archive)
} ORDER BY ?label"""
    result = requests.post(config.TRIPLESTORE_URL,
        data={"query": INSTITUTIONS_SPARQL,
              "format": "json"})
    for binding in result.json().get("results").get("bindings"):
        INSTITUTIONS[binding.get("institution").get("value")] = \
        binding.get("label").get("value")


def report_router(report_name):
    if len(INSTITUTIONS) < 1:
        __init_institutions__()
    if report_name.startswith("institution-count"):
        return institution_counts()
    if report_name.startswith("rights-statements"):
        return rights_statements()

def institution_counts():
    output = {"total": 0, "institutions": []}
    sparql = PREFIX + """
SELECT ?institution (count(?instance) as ?instance_count)
WHERE {
     ?instance rdf:type bf:Instance .
     ?item bf:itemOf ?instance ;
           bf:heldBy ?institution .

} GROUP BY ?institution"""
    result = requests.post(config.TRIPLESTORE_URL,
        data={"query": sparql,
              "format": "json"})
    bindings = result.json().get('results').get('bindings')
    for row in bindings:
        institution_iri = row.get("institution").get("value")
        count = row.get("instance_count").get("value")
        label = INSTITUTIONS.get(institution_iri)
        output["institutions"].append(
            {"label": label,
             "url": institution_iri,
             "count": count})
        output['total'] += int(count)
    sorted(output['institutions'], key=lambda x: x['label'])
    return output
        
    
def rights_statements():
    output = []
    sparql = PREFIX + """
SELECT ?rights_statement (count(?item) as ?count) WHERE{
  ?item rdf:type bf:Item ;
  OPTIONAL { ?item bf:AccessPolicy ?rights_statement }
  OPTIONAL { ?item bf:usageAndAccessPolicy ?rights_statement }
  
} GROUP BY ?rights_statement"""
    result = requests.post(config.TRIPLESTORE_URL,
        data={"query": sparql,
              "format": "json"})
    bindings = result.json().get("results").get("bindings")
    for row in bindings:
        output.append({"url": row.get("rights_statement", 
                                      {'value': 'Unknown'}).get('value'),
                       "count": row.get("count").get('value')})
    return output


__author__ = "Jeremy Nelson"


import datetime
import os
import sys
import requests
import click
from zipfile import ZipFile, ZIP_DEFLATED
from multiprocessing import Pool
import bibcat.rml.processor as processor

BF2MAP4 = processor.SPARQLBatchProcessor(
    rml_rules=['bf-to-map4-alt.ttl'],
    triplestore_url='')

CONTEXT = {"edm": "http://www.europeana.eu/schemas/edm/",
           "dcterms": "http://purl.org/dc/terms/",
	   "org": "http://www.openarchives.org/ore/terms"}

def transform(triplestore_url, instance_iri):
    result = requests.post(triplestore_url,
        data={"query": ITEM_SPARQL_TEMPLATE.format(instance_iri=instance_iri),
              "format": "json"})
    if result.status_code > 399:
        return
    item_bindings = result.json().get("results").get("bindings")
    item_iri = item_bindings[0].get("item").get('value')
    BF2MAP4.triplestore_url = triplestore_url
    BF2MAP4.run(instance_iri=instance_iri,
                item_iri=item_iri)
    output = BF2MAP4.output.serialize(
        format='json-ld',
        context=CONTEXT)
    return output

@click.command()
@click.option("--triplestore_url")
@click.option("--project_base")
@click.option("--offset", help="Instance offset", default=0)        
def processing(triplestore_url, project_base, offset=0):
    result = requests.post(triplestore_url,
        data={"query": INSTANCES_SPARQL_TEMPLATE.format(offset),
              "format": "json"})
    bindings = result.json().get('results').get('bindings')
    file_name = "ms-{}-{:03}.zip".format(
        datetime.datetime.utcnow().toordinal(),
        offset)
    tmp_location = os.path.join(project_base, 
                                "dump/{}".format(file_name))
    
    dump_zip = ZipFile(tmp_location,
        mode="w",
        compression=ZIP_DEFLATED,
        allowZip64=True)
    start = datetime.datetime.utcnow()
    click.echo("Starting Pool at {}".format(start))
    with Pool(processes=4) as pool:
        for i,row in enumerate(bindings):
            instance_iri = row.get("instance").get("value")
            key = instance_iri.split("/")[-1]
            if "date" in row:
                date = row.get("date")
            else:
                date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            res = pool.apply_async(transform, (triplestore_url, instance_iri))
            if res is None:
                continue
            dump_zip.writestr("resourecs/{}.json".format(key),
                              res.get())
            if not i%25 and i>0:
                click.echo(".", nl=False)
            if not i%100:
                click.echo("{:,}".format(i), nl=False)
    
    end = datetime.datetime.utcnow()
    click.echo("Finished at {}, total time {} min".format(end,
        (end-start).seconds / 60.0)) 
    dump_zip.close()
        

PREFIX = """PREFIX bf: <http://id.loc.gov/ontologies/bibframe/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX relators: <http://id.loc.gov/vocabulary/relators/>
PREFIX schema: <http://schema.org/>
"""

INSTANCES_SPARQL_TEMPLATE = PREFIX + """

SELECT DISTINCT ?instance ?date
WHERE {{
    ?instance rdf:type bf:Instance .
    OPTIONAL {{ 
        ?instance bf:generationProcess ?process .
        ?process bf:generationDate ?date .
    }}
}} ORDER BY ?instance
LIMIT 50000
OFFSET {0}"""

ITEM_SPARQL_TEMPLATE = PREFIX + """
SELECT DISTINCT ?item
WHERE {{
     ?item bf:itemOf <{instance_iri}> .
}}"""
   

if __name__ == "__main__":
    processing() 

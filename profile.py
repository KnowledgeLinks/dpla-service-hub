"""Profile Command-Line Utilities for DP.LA Service Hub Aggregator Feed"""
__author__ = "Jeremy Nelson, Mike Stabile"

import click
import csv
import datetime
import logging
import os
import rdflib
import requests
import sys

PROJECT_BASE =  os.path.abspath(os.path.dirname(__file__))
sys.path.append(PROJECT_BASE)

logging.getLogger("rdfw.rdfframework").setLevel(logging.CRITICAL)
logging.getLogger("passlib").setLevel(logging.CRITICAL)

def iterate_dc_xml(**kwargs):
    from bibcat.ingesters.ingester import new_graph
    import xml.etree.ElementTree as etree
    filepath = kwargs.get("in_file")
    ingester = kwargs.get("ingester")
    shard_size = kwargs.get("shard_size", -1)
    output_dir = kwargs.get("output_dir", 
        os.path.abspath(os.path.join(PROJECT_BASE, "output")))
    start = datetime.datetime.utcnow()
    click.echo("Starting DC XML at {} for records at {}".format(
        start,
        filepath))
    count = 0
    shard_template = "dc-{}k-{}k.ttl"
    if shard_size is not None and shard_size > 0:
        shard_name = shard_template.format(count, shard_size)
    shard_graph = new_graph()
    for event, elem in etree.iterparse(filepath):
        if event.startswith('end') and \
           elem.tag.endswith("Description"):
            ingester.transform(etree.tostring(elem))
            shard_graph += ingester.graph
            if not count%10 and count > 0:
                click.echo(".", nl=False)
                #! DEBUG code
                with open(os.path.join(output_dir, "dpl-dc-test.ttl"), "wb+") as fo:
                    fo.write(shard_graph.serialize(format='turtle'))
                break
            if not count%100:
                click.echo(count, nl=False)
            if shard_size is not None and shard_size > 0 and not count%shard_size:
                with open(os.path.join(output_dir, shard_name), 'wb+') as fo:
                    fo.write(shard_graph.serialize(format='turtle'))
                shard_graph = new_graph()
                shard_name = shard_template.format(count, count+shard_size)
            count += 1
    end = datetime.datetime.utcnow()
    click.echo("Finished DC ingestion at {} total time of {} mins for {}".format(
        end,
        (end-start).seconds / 60.0,
        count))


def oai_handler(**kwargs):
    from bibcat.ingesters.oai_pmh import OAIPMHIngester
    ingester = OAIPMHIngester(repository=kwargs.get('url'))

def islandora_handler(**kwargs):
    from bibcat.ingesters.oai_pmh import IslandoraIngester
    ingester = IslandoraIngester(repository=kwargs.get('url'),
                   rules_ttl=kwargs.get('profile'))
    ingester.harvest()

@click.group()
def cli():
    pass

@click.command()
@click.argument('profile')
@click.option('--ingest_type', 
    help='Ingester type',
    type=click.Choice(['dc', 
                       'csv', 
                       'islandora', 
                       'oai_pmh', 
                       'ptfs'])) 
@click.option('--in_file',
    default=None, 
    help='Metadata Input File with multiple records')
@click.option('--in_dir',
    default=None, 
    help='Directory contain Metadata')
@click.option('--at_url',
    default=None,
    help="URL to sitemap, resourceSync, or OAI_PM feeds")
@click.option('--shard_size',
    default=None,
    help='Saves output RDF triples in different shard files')
@click.option('--output_dir',
    default=None,
    help="Output directory for generated RDF turtle files")
def add_batch(ingest_type, 
    profile, 
    in_file, in_dir, at_url, shard_size, output_dir):
    """Provides multiple ways to batch ingest metadata records
    as BIBFRAME Linked Data with output as RDF Turtle files"""
    click.echo("Running Add Batch")
    profile_path = os.path.abspath(os.path.join(PROJECT_BASE,
        os.path.join("custom", profile)))
    if not os.path.exists(profile_path):
        raise ValueError("Profile RDF Rule {} not found".format(
            profile_path))
    if ingest_type.startswith("csv"):
        from bibcat.ingesters import csv as csv_ingester
        from bibcat.ingesters.ingester import new_graph
        if in_file is not None:
            pass
        reader = csv.DictReader(open(in_file, errors='ignore'))
        ingester = csv_ingester.RowIngester(rules_ttl=profile)
        all_graph = new_graph()
        for i, row in enumerate(reader):
            ingester.transform(row)
            all_graph += ingester.graph
            if not i%10 and i > 0:
                click.echo(".", nl=False)
            if not i%100:
                click.echo(i, nl=False)
        with open(os.path.join(output_dir, 'dpla-csv.ttl'), 'wb+') as fo:
            fo.write(all_graph.serialize(format='turtle'))
    elif ingest_type.startswith("dc"):
        from bibcat.ingesters import dc
        ingester = dc.DCIngester(rules_ttl=profile)
        if in_file is not None:
            iterate_dc_xml(in_file=in_file,
                ingester=ingester,
                shard_size=shard_size,
                output_dir=output_dir)
    elif ingest_type.startswith("islandora"):
        islandora_handler(url=at_url, profile=profile)
    elif ingest_type.startswith("oai_pmh"):
        pass
    
        

@click.command()
@click.argument('profile')
@click.option('--ingest_type', 
    help='Ingester type',
    type=click.Choice(['dc', 'csv', 'mods', 'ptfs'])) 
@click.option('--item_iri', default=None, help="Optional IRI for Item")
@click.option('--in_file',  default=None, help='Metadata Input File')
@click.option('--at_url', default=None, help='Metadata Input URL')
@click.option('--out_file', default=None, help='Saves output to RDF Turtle file')
def add_record(profile, ingest_type, in_file, at_url, item_iri, out_file):
    """Takes a RDF ttl Rule file called a profile, a metadata input file,
    and either outputs to an RDF BIBFRAME turtle file or to the RDF triplestore
    defined in the application's configuration.
    """
    click.echo("Running Add Record")
    profile_path = os.path.abspath(os.path.join(PROJECT_BASE,
        os.path.join("custom", profile)))
    if not os.path.exists(profile_path):
        raise ValueError("Profile RDF Rule {} not found".format(
            profile_path))
    if in_file is None and at_url is None:
        raise ValueError("Profile must have either an URL or local file")
    if in_file is not None:
        if not os.path.exists(in_file):
            raise ValueError("Input file path {} not found".format(
                in_file))
        else:
            with open(in_file, 'rb') as fo:
                try: # Try utf-8 default encoding
                    raw_src = fo.read().decode()
                except UnicodeDecodeError:
                    raw_src = fo.read().decode('utf-16')
    elif at_url is not None:
        result = requests.get(at_url)
        result.encoding = 'utf-8'
        if result.status_code < 399:
            raw_src = result.text
    else:
        raise ValueError("Missing input file or url")
  
    if ingest_type.startswith("mods"):
        from bibcat.ingesters import mods
        ingester = mods.MODSIngester(rules_ttl=profile,
                       source=raw_src)
        # Add Marmot NS
        ingester.xpath_ns["marmot"] = "http://marmot.org/local_mods_extension"
    elif ingest_type.startswith("ptfs"):
        from bibcat.ingesters import ptfs
        ingester = ptfs.PTFSIngester(rules_ttl=profile,
                       source=raw_src)
    else:
        raise ValueError("Ingester Type {} not found".format(ingest_type))
    if item_iri is not None:
        item_iri = rdflib.URIRef(item_iri)
    ingester.transform(item_uri=item_iri)
    if out_file is not None:
        with open(out_file, 'wb+') as fo:
            fo.write(ingester.graph.serialize(format='turtle'))
    else:
        ingester.add_to_triplestore()
    click.echo("Finished Add Records")

cli.add_command(add_batch)
cli.add_command(add_record)

if __name__ == '__main__':
    cli()

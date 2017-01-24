"""Profile Command-Line Utilities for DP.LA Service Hub Aggregator Feed"""
__author__ = "Jeremy Nelson, Mike Stabile"

import click
import logging
import os
import sys

PROJECT_BASE =  os.path.abspath(os.path.dirname(__file__))
sys.path.append(PROJECT_BASE)

logging.getLogger("rdfw.rdfframework").setLevel(logging.CRITICAL)

@click.group()
def cli():
    pass

@click.command()
@click.option('--ingest_type', 
    help='Ingester type',
    type=click.Choice(['dc', 'csv', 'mods', 'oai_pmh', 'ptfs'])) 
@click.option('--profile', help='Profile RDF Turtle file')
@click.option('--in_file',  help='Metadata Input File')
@click.option('--out_file', default=None, help='Saves output to RDF Turtle file')
def add(profile, ingest_type, in_file, out_file):
    """Takes a RDF ttl Rule file called a profile, a metadata input file,
    and either outputs to an RDF BIBFRAME turtle file or to the RDF triplestore
    defined in the application's configuration.
    """
    click.echo("Running Add Records")
    profile_path = os.path.abspath(os.path.join(PROJECT_BASE,
        os.path.join("custom", profile)))
    if not os.path.exists(profile_path):
        raise ValueError("Profile RDF Rule {} not found".format(
            profile_path))
    if not os.path.exists(in_file):
        raise ValueError("Input file path {} not found".format(
            in_file))
    else:
        with open(in_file, 'rb') as fo:
            raw_src = fo.read() 
    if ingest_type.startswith("csv"):
        from bibcat.ingesters import csv
        ingester = csv.RowIngester(rules_ttl=profile,
            source=raw_src)
    elif ingest_type.startswith("dc"):
        from bibcat.ingesters import dc
        ingester = dc.DCIngester(rules_ttl=profile,
            source=raw_src)
    elif ingest_type.startswith("mods"):
        from bibcat.ingesters import mods
        ingester = mods.MODSIngester(rules_ttl=profile,
                       source=raw_src.decode())
    elif ingest_type.startswith("ptfs"):
        from bibcat.ingesters import ptfs
        ingester = ptfs.PTFSIngester(rules_ttl=profile,
                       source=raw_src)
    else:
        raise ValueError("Ingester Type {} not found".format(ingest_type))
    ingester.transform()
    if out_file is not None:
        with open(out_file, 'wb+') as fo:
            fo.write(ingester.graph.serialize(format='turtle'))
    click.echo("Finished Add Records")
    
    


    
    

cli.add_command(add)

if __name__ == '__main__':
    cli()

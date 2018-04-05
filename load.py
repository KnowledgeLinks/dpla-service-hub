__author__ = "Jeremy Nelson"

import click

from rdfframework.configuration import RdfConfigManager
from rdfframework import rdfclass
from rdfframework import search
import os, sys, pdb

from api import generate_resource_dump, app, CONFIG_MANAGER

def setup_dpla_indexing():
    CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
   
    conf_mgr = CONFIG_MANAGER
    click.echo("Configuration Manager {}".format(conf_mgr))
    mappings = search.EsMappings()
    mappings.initialize_indices()
    click.echo("Finished initialized ES mapping Indices")
    dpla_search = search.EsRdfBulkLoader(
      rdfclass.bf_Work,
      conf_mgr.conns.datastore,
      conf_mgr.conns.search,
      no_threading=False,
      idx_only_base=True)
    click.echo("Generating Resource Dump")
    resource_dump = generate_resource_dump()
    tmp_location = os.path.join(conf_mgr.dirs.dump, 
      "resourcedump.xml")
    with open(tmp_location, 'w+') as fo:
        fo.write(resource_dump.as_xml())


if __name__ == "__main__":
    setup_dpla_indexing()

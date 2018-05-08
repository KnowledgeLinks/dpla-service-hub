__author__ = "Jeremy Nelson"

import click
import subprocess
import json

from rdfframework.configuration import RdfConfigManager
from rdfframework import rdfclass
from rdfframework import search
from rdfframework import sparql
import bibcat
import os, sys, pdb

from api import generate_resource_dump, app, CONFIG_MANAGER, STATISTICS_COUNTS

def cleanup_data(queries, name):
    """
    runs cleanup queries
    """
    conn = CONFIG_MANAGER.conns.datastore

    click.echo("Running '%s' cleanup queries." % name)
    results = sparql.run_query_series(queries, conn)
    click.echo("Finished cleanup queries")
    for i, result in enumerate(results):
        click.echo(sparql.read_query_notes(queries[i]))
        click.echo(result + "\n\n")
    click.echo("bibframe primary class counts:")
    result = conn.query(bibcat.sparql.summary.CLASS_COUNTS, rtn_format="csv")
    click.echo("\n".join(["{0: <16}{1: <16}".format(*item.split(","))
                          for item in result.split("\r\n")
                          if item]))

def setup_dpla_indexing():
    CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))

    conf_mgr = CONFIG_MANAGER
    click.echo("Configuration Manager {}".format(conf_mgr))
    mappings = search.EsMappings()
    mappings.initialize_indices(action='reset')
    click.echo("Finished initialized ES mapping Indices")
    dpla_search = search.EsRdfBulkLoader(
        rdfclass.bf_Work,
        conf_mgr.conns.datastore,
        conf_mgr.conns.search,
        no_threading=True,
        reset_idx=True,
        idx_only_base=True)
    click.echo("Generating Resource Dump")
    resource_dump = generate_resource_dump(True)
    tmp_location = os.path.join(conf_mgr.dirs.dump,
      "resourcedump.xml")
    with open(tmp_location, 'w+') as fo:
        fo.write(resource_dump.as_xml())
    subprocess.run(["docker",
                    "cp",
                    "/home/p2p_user/tmp/dump/.",
                    "dplaservicehub_bibcat_1:/opt/dpla-service-hub/dump"])


UW_MISSING_HELD_BY_QRY = """
# UW_MISSING_HELD_BY_QRY
# Adds missing bf:heldBy info for UWY records

prefix bf: <http://id.loc.gov/ontologies/bibframe/>
INSERT {
  ?item bf:heldBy <http://www.uwyo.edu/>
}
WHERE
{
    {
        ?item a bf:Item .
        optional {
            ?item bf:heldBy ?org .
        }
        filter(!(bound(?org)))
    }
    FILTER (CONTAINS(LCASE(STR(?item)), "uwdigital"))
}
"""


if __name__ == "__main__":
    cleanup_data(bibcat.sparql.cleanup.CLEANUP_QRY_SERIES,"1:1 resolution")
    cleanup_data(bibcat.sparql.cleanup.CLEANUP_MISSING_TITLE_SERIES,
                 "Missing Title Removal")
    cleanup_data([UW_MISSING_HELD_BY_QRY],
                 "Missing UW heldby")
    setup_dpla_indexing()
    STATISTICS_COUNTS.print()

__author__ = "Jeremy Nelson"

from rdfframework.configuration import RdfConfigManager
from rdfframework import rdfclass
from rdfframework import search
import os, sys, pdb


def setup_dpla_indexing():
        current_path = os.path.abspath(os.path.dirname(__file__))
        print("Current path is {}".format(current_path))
        sys.path.append("{}/instance".format(current_path))
        print("Importing config")
        import config
        conf_mgr = RdfConfigManager(config.__dict__)
        print("Configuration Manager {}".format(conf_mgr))
        mappings = search.EsMappings()
        mappings.initialize_indices()
        print("Finished initialized ES mapping Indices")
        dpla_search = search.EsRdfBulkLoader(
            rdfclass.bf_Work,
            conf_mgr.conns.datastore,
            conf_mgr.conns.search,
            no_threading=False,
            idx_only_base=True)

if __name__ == '__main__':
    setup_dpla_indexing()

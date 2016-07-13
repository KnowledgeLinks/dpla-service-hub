"""REST API for DP.LA Service Hub BIBCAT Aggregator Feed"""
__author__ = "Jeremy Nelson, Mike Stabile"

import falcon
import json
import xml.etree.ElementTree as etree

class OAIPMHRepository(object):
    """Open Archives Initiative Protocol for Metadata Harvesting (OAI-PMH)
    REST API <https://www.openarchives.org/pmh/>"""

    def on_get(self, req, resp):
        """HTTP GET response handler

        Args:
            req(falcon.Request): Falcon Request object
            resp(falcon.Response): Falcon Response object
        """
        verb = req.get_param("verb")
        resp.status = falcon.HTTP_200
        if verb.startswith("GetRecord"):
            identifier = req.get_param("identifier")
            metadataPrefix = req.get_param("metadataPrefix")
        if verb.startswith("Identify"):
            pass
        if verb.startswith("ListIdentifiers"):
            pass


    

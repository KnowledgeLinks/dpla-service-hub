"""REST API for DP.LA Service Hub BIBCAT Aggregator Feed"""
__author__ = "Jeremy Nelson, Mike Stabile"

import click
import json
import xml.etree.ElementTree as etree
import requests
import urllib.parse
from flask import Flask, request, render_template, Response
from flask_restful import Resource, Api, reqparse

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')
api = Api(app)

parser = reqparse.RequestParser()
parser.add_argument('initiate', type=str, help="OAI-PMH Harvester")

@api.representation('text/xml')
def output_xml(data, code, headers=None):
    resp = app.make_response(data)
    return resp
    


class StaticRepositoryGateway(Resource):
    """Open Archives Initiative Protocol for Metadata Harvesting (OAI-PMH)
    REST API <https://www.openarchives.org/pmh/>"""

    def __intermediation__(self, static_repo_url):
        """Method takes a Static Repository URL and returns a repository 
        object for use in the OAI-PMH xml template in the format of 
        http://host:port/path/file.

        Args:
            static_repo_url(str): URL for repository
        """
        oai_info = {}
        url_parts = urllib.parse.urlparse(static_repo_url)
        institution_url = "{}://{}".format(url_parts.scheme, url_parts.netloc)
        oai_info['baseURL'] = institution_url
        identify_result = requests.post(
            app.config.get("TRIPLESTORE_URL"),
            data={"query": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?name
WHERE {{
    <{0}> rdfs:label ?name .
}}""".format(institution_url)})
        if identify_result.status_code > 300:
            raise Exception("Cannot retrieve {}".format(institution_url))
        oai_info['name'] = identify_result.json().get('results').get('bindings')[0]\
                           .get('name').get('value')
        
        return oai_info    
                         
    def get(self):
        """HTTP GET response handler"""
        args = parser.parse_args()
        static_repo_url = args.get('initiate')
        if static_repo_url is not None:
            oai_xml = render_template('oai-pmh.xml', 
                repo=self.__intermediation__(static_repo_url))
            return output_xml(oai_xml, None, None)
        return {"message": "OAI-PMH Static Repository Gateway"}

api.add_resource(StaticRepositoryGateway, "/oai")

if __name__ == '__main__':
    app.run(debug=True)

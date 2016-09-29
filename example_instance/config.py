"""OMNIBUS CONFIG file for KnowlegeLinks.io applications"""
# enter a secret key for the flask application instance
SECRET_KEY = "enter_a_secret_key_here"

# URL used in generating IRIs
BASE_URL = "http://bibcat.org/"

# Database REST urls
TRIPLESTORE_URL = "http://localhost:9999/blazegraph/sparql"
REPOSITORY_URL = "http://localhost:8080/rest"
ES_URL = "http://localhost:9200"
# Dictionary of web accessibale datasets
DATASET_URLS = {
    "loc_subjects_skos.nt.gz": "http://id.loc.gov/static/data/authoritiessubjects.nt.skos.gz",
    "marc_relatoes_nt": "http://id.loc.gov/static/data/vocabularyrelators.nt.zip",
    "bibframe_vocab_rdf": "http://id.loc.gov/ontologies/bibframe.rdf"
}
DEFAULT_RDF_NS = {
    "kds": "http://knowledgelinks.io/ns/data-structures/",
    "kdr": "http://knowledgelinks.io/ns/data-resources/",
    "bf": "http://id.loc.gov/ontologies/bibframe/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "loc": "http://id.loc.gov/authorities/",
    "mods": "http://www.loc.gov/mods/v3",
    "dc": "http://purl.org/dc/terms/",
    "es": "http://knowledgelinks.io/ns/elasticsearch/",
    "schema": "http://schema.org/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "void": "http://rdfs.org/ns/void#",
    "dcterm": "http://purl.org/dc/terms/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dbo": "http://dbpedia.org/ontology/",
    "dbp": "http://dbpedia.org/property/",
    "dbr": "http://dbpedia.org/resource/"
}
# this is the graph name where application definitions are stored
RDF_DEFINITION_GRAPH = "<http://knowledgelinks.io/ns/application-framework/>"
# this is the graph name where reference triples are stored
RDF_REFERENCE_GRAPH = "<http://knowledgelinks.io/ns/bibframe/reference/>"
RDF_LOC_SUBJECT_GRAPH = "<http://knowledgelinks.io/ns/bibframe/loc_subject/>"
# The name used the site
SITE_NAME = "BIBCAT 2.0"

# Organzation information for the hosting org.
ORGANIZATION = {
   "name": "knowledgeLinks.io",
   "url": "http://knowledgelinks.io/",
   "description": ""
}

# Default data to load at initial application creation
FRAMEWORK_DEFAULT = [
        {
                # add a default user
                "form_path" : "UserForm/NewForm",
                "form_data" : {
                        "emailaddr": "user@example.com",
                        "givenname": "Firstname",
                        "familyname": "Lastname",
                        "username": "example_user",
                        "password": "password"
                }
        },
        {
                # a a default organization
                "form_path" : "organization/new",
                "form_data" : {
                        "website": ORGANIZATION['url'],
                        "orgname": ORGANIZATION['name'],
                        "itemDescription": ORGANIZATION['description']
                }
        }
]

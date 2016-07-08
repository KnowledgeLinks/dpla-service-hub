[BC]: https://github.com/KnowledgeLinks/rdfw-bibcat
[BF]: https://www.loc.gov/bibframe/docs/index.html
[BG]: https://www.blazegraph.com/
[DC]: http://dublincore.org/
[DOCK]: https://www.docker.com/
[DPLA]: https://dp.la/
[HOME]: https://github.com/KnowledgeLinks/dpla-service-hub
[KL]: http://knowledgelinks.io/
[MARC]: https://www.loc.gov/marc/
[MODS]: https://www.loc.gov/standards/mods/
[OAIPMH]: https://www.openarchives.org/pmh/
[RDFF]: http://knowledgelinks.io/products/rdfframework/index.html

# DP.LA Service Hub
This [project][HOME] provides a lightweight [DP.LA][DPLA] aggregation feed and 
a command-line interface for ingesting different
bibliographic and metadata vocabularies like [MODS][MODS], 
[Dublin Core][DC], and [MARC][MARC] into a [RDF triplestore][BL] as
[BIBFRAME 2.0][BF] linked-data. This project is based [KnowledgeLinks.io][KL]'s Catalog Pull 
Platform using the [RDF Framework][RDFF] and [BIBCAT][BC]. 

This project started as a pilot for the Colorado/Wyoming [DP.LA][DPLA] 
service hub. 

## Setup

1.  Clone or fork the [project repository][HOME]:

    git clone https://github.com/KnowledgeLinks/dpla-service-hub.git 

1.  Initialize and update submodules

    cd dpla-service-hub/
    git submodule init
    git submodule update

1.  Create an instance directory for configuration and custom RDF rules:

    mkdir instance
    cd instance/
    touch config.py

### Config.py options
To configure [dpla-service-hub][HOME], you'll need to add these minimum 
variables in your `config.py` file.

## Ingestion

### Customizing 

### MARC 21

### MODS XML

### Dublin Core XML

### Dublin Core CSV

## Deploying

### With Docker

### Server Aggregation Feed


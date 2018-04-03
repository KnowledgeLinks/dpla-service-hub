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

## Setup for Pilot

1.  Clone [project][HOME] to the `/opt/` directory.
1.  Make an instance directory at `/opt/dpla-service-home/`
1.  Make an uploads directory at `/opt/dpla-service-home/` (or any other location 
    specified in `config.py`).
1.  Create a `config.py` in the new `/opt/dpla-service-home/instance/` directory
    and specify two triplestore connections (**plains2peaks** and **active_defs**)
    and one Elasticsearch connection called **search**.
1.  SFTP the current contents `data` directory in the Plains2Peaks repository at 
    https://github.com/KnowledgeLinks/Plains2PeaksPilot to the `/opt/dpla-service-hub/uploads`
    directory.
1.  Launch `docker-compose up` to download and/or build images for the service hub. You may
    need to restart the bibcat container with `docker-compose restart bibcat`.
1.  In separate command-line, launch `python load.py` to index the triples into Elasticsearch 


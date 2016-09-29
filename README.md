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

    ```
    git clone https://github.com/KnowledgeLinks/dpla-service-hub.git
    ``` 

1.  Initialize and update submodules

    ```
    cd dpla-service-hub/
    git submodule init
    git submodule update
    ```

1.  Create an instance directory for configuration and custom RDF rules:

    ```
    mkdir instance
    cd instance/
    touch config.py
    ```

### Config.py options
To configure [dpla-service-hub][HOME], you'll need to add these minimum 
variables in your `config.py` file.

## Ingestion
Right now, the way to ingest records into the triplestore is open an 
interactive Python 3 session. Here is an example of
setting-up your Python environment to use the these different types of
source ingesters into the triplestore:

```python
import sys
sys.path.append("/dpla-service-hub/bibcat")
from ingesters.ingester import NS_MGR, new_graph
```

### Customizing 
To customize the field mappings, add common properties, and other 
information to the triplestore, add Turtle RDF files in the `custom` 
directory. When you then create an ingester, include the title of the
turtle file with the **custom** parameter to use your custom rules
during the ingestion period.


### MARC 21
Create a MARC21 ingester using a custom RDF rules graph for Colorado College 
along with a sample of Colorado College's MARC 21 records:

```python
import pymarc
import ingesters.marc as marc2bf
marc_ingester = marc2bf.MARCIngester(custom=['cc-marc-bf-.ttl'])
with open("dpla-service-hub/tmp/cc-marc.mrc", "rb") as fo:
    reader = pymarc.MARCReader(fo, to_unicode=True)
for record in reader:
    marc_ingester.transform(record=record)
```

### MODS XML

```python
import requests
import xml.etree.ElementTree as etree
import ingesters.mods as mods
mods_ingester = mods.MODSIngester(mods_xml, custom=["cc-mods-bf.ttl"])
```

Request the MODS XML datafile from a Colorado College's Islandora repository 
for a single Fedora Object:

```python
mods_result = request.get("https://digitalcc.coloradocollege.edu/islandora/object/coccc:26262/datastream/MODS/view")
mods_xml = etree.XML(mods_result.text)
mods_ingester.transform(source=mods_xml)
```

### Dublin Core XML
To test a random collection of Dublin Core RDF XML from Denver Public Library

```python 
import pickle
import pymarc
import ingesters.dc as dc
dc_ingester = dc.DCIngester(custom=['dpl-dc.ttl'])
with open("dpla-service-hub/tmp/sample_recs.pickle", "rb") as fo:
    sample_recs = pickle.load(fo)
for rdf_record in sample_recs:
    dc_ingester.transform(xml=etree.tostring(rdf_record))
    dc_ingester.add_to_triplestore()
```

### Dublin Core CSV


## Deploying

### With Docker

### Server Aggregation Feed


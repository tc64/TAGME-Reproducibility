Setup
=====

In order to setup and run our implementation of TAGME, install [PyLucence](https://lucene.apache.org/pylucene/) and the packages listed in ``requirements.txt`` file.

Once the required packages are installed, you need to have the resources required for running the code, which are: (i) a surface form dictionary and (ii) indices for a Wikipedia dump.

You can directly ask the authors of [1] to provide you with these resources or build them using the following steps:

 1. Downloading a Wikipedia dump
 2. Preprocessing the dump
 3. Building indices
 4. Building a surface form dictionary
 5. Setting the config file

Below we describe each of these steps.


1. Downloading a Wikipedia dump
-------------------------------

Our TAGME is built based on a Wikipedia dump; i.e., ``enwiki-YYYYMMDD-pages-articles.xml.bz2`` file that can be downloaded from [here](http://dumps.wikimedia.org/enwiki/).  

For the experiments in [1], we used the dumps from *20100408* and *20120502*, which are available upon request. 


2. Preprocessing the dump
-----------------------
The [Wikipedia Extractor](http://medialab.di.unipi.it/wiki/Wikipedia_Extractor) tool is used for preprocessing of the Wikipedia dump.  The dump used for experiments is availble under `lib/wikiextractor-master`.

The following command is executed to pre-process the dumps.  Mind that the `-l` option is necessary, as it preserves the links.

```
python tagme-rep/lib/wikiextractor-master/WikiExtractor.py -o path/to/output/folder -l path/to/enwiki-YYYYMMDD-pages-articles.xml.bz2
```

We assume that the resulting files are stored under `preprocessed-YYYYMMDD` folder.

3. Building indices
------------------

 Two type of indices are built from the Wikipedia dumps:
  
  - **YYYYMMDD-index**: Index of Wikipedia articles (with resolved URIs).
  - **YYYYMMDD-index-annot**: Index containing only Wikipedia annotations. This index is used to compute relatedness between entities.

Run the following commands to build these indices:

1. ``python -m nordlys.wikipedia.indexer -i preprocessed-YYYYMMDD/ -o YYYYMMDD-index/``

2. ``python -m nordlys.wikipedia.indexer -a -i preprocessed-YYYYMMDD/ -o YYYYMMDD-index-annot/``


We note that the following pages are ignored from the indices:

 - **List pages**: Wikipedia URIs starting with "<wikipedia:List_of" OR "<wikipedia:Table_of".
 - **Disambiguation pages**: Articles [ending with "(disambiguation)"] OR [containing "may refer to:" AND having lass than 200 words].
 - **Redirect pages**: These pages are excluded while pre-processing of Wikipedia articles (i.e. by the WikiExtractor).

4. Building a surface form dictionary
-------------------------------------

The surface form dictionary is built from these sources:

 - Redirect pages
 - Anchor texts of Wikipedia articles
 - Wikipedia page titles and their variants (removing parts after the comma or in parentheses)

Below we describe how to build each source and merge them into as a signle dictionary.

### Redirect pages:

We used [Wikipedia Redirect](https://code.google.com/p/wikipedia-redirect/) tool to extract the redirect pages from the original dump, which is available under  `lib/edu.cmu.lti.wikipedia_redirect`.

Run the following commands under the main code directory:

  - ``bunzip2 path/to/enwiki-YYYYMMDD-pages-articles.xml.bz2``
  - ``cd lib/edu.cmu.lti.wikipedia_redirect``
  - ``javac src/edu/cmu/lti/wikipedia_redirect/*.java``
  - ``java -cp src edu.cmu.lti.wikipedia_redirect.WikipediaRedirectExtractor path/to/enwiki-YYYYMMDD-pages-articles.xml``

The resulting file is `redirects.txt`.

### Anchor texts:

The anchor texts file are extracted using the following commands:

- ``python -m nordlys.wikipedia.annot_extractor -i /path/to/preprocessed-YYYYMMDD/ -o /path/to/annotations-YYYYMMDD/``

- ``python -m nordlys.wikipedia.anchor_extractor -i /path/to/annotations-YYYYMMDD/ -o path/to/output/folder``

The resulting file is `anchors_count.txt`.

### Wikipedia page titles:

The following command extracts page id and title for all Wikipedia articles:

```python -m nordlys.wikipedia.pageid_extractor -in /data/wikipedia/preprocessed-YYYYMMDD/ -o path/to/output/folder```

The resulting file is `page-id-titles.txt`.


### Merging all sources:

Once all the above sources are built, run the following command to merge them all into a single Json file

```python -m nordlys.wikipedia.merge_sf -redirects path/to/redirects.txt -anchors path/to/anchors_count.txt -titles path/to/page-id-titles.txt -o path/to/output/folder```
    
The resulting file is `sf_dict_mongo.json`, which can be directly imported to a MongoDB collection using this command:

```mongoimport --db nordlys --collection surfaceforms_wiki_YYYYMMDD --file /path/to/sf_dict_mongo.json --jsonArray```

5. Setting the config file
----------------------
 
One all the resources are built, you need to change the following lines in the ``nordlys/tagme/config.py`` file: 

```
COLLECTION_SURFACEFORMS_WIKI = "surfaceforms_wiki_YYYYMMDD"
```
```
INDEX_PATH = "path/to/YYYYMMDD-index"
INDEX_ANNOT_PATH = "path/to/YYYYMMDD-index-annot"
```

Contact
-------

If you have any questions, feel free to contact Faegheh Hasibi at <faegheh.hasibi@idi.ntnu.no>.


```
[1]  F. Hasibi, K. Balog, and S.E. Bratsberg. “On the reproducibility of  the TAGME Entity Linking System”, In proceedings of 38th European Conference on Information Retrieval (ECIR ’16), Padova, Italy, March 2016.
```
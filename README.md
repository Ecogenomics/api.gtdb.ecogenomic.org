# GTDB API

This repository contains the source code to [GTDB API](https://api.gtdb.ecogenomic.org/).

There are two main components:

* `API` - interfaces the database with the website.
* `FastANI` - spawns [RedisQueue](https://python-rq.org/) workers for the FastANI tool queue.

## Contributing

This project uses [Semantic Versioning](http://semver.org/) and [Conventional Commits](https://conventionalcommits.org/)
to automatically generate release notes using [Semantic Release](https://semantic-release.gitbook.io/semantic-release/).

Please ensure that your commits are property formatted.

## Running locally

__Note__: [Poetry](https://python-poetry.org/) is being used as a package manager for this project, ensure it is on the
CLI.

Ensure the `.env` file is populated with the correct information.

### Python

```shell
cd /path/to/repository
export PYTHONPATH=/path/to/repository
poetry install
python main.py
```

The server will then be running on http://localhost:9000

### Docker

```shell
cd /path/to/repository
docker-compose up
```

## Scripts

### Updating the FastANI database

This will ensure that the FastANI database is up to date on disk (i.e. has downloaded all new genomes).

They are stored on a mounted volume at `/mnt/ncbi-genomes/ncbi` on the website VM. The index of those genomes are stored in the `fastani` database, in the `genome` table, 
they must be present in that table for FastANI to recognise the genome.

This is done by running the following script within the context of the container:

```shell
cd /mnt/gtdb-website/repos/api.gtdb.ecogenomic.org
docker build -t ncbi-db -f docker/ncbi-db/Dockerfile .
nice docker run --rm --network gtdb-stack-config_default -e PYTHONPATH=/api -v /mnt/ncbi-genomes/ncbi:/mnt/ncbi-genomes/ncbi -it ncbi-db python scripts/update_fastani_db.py
```

### Updating GTDB tree links

These are the links that are present in the tree viewer (e.g. Bergeys, LPSN, NCBI, SandPiper, SeqCode)..

For the website to recognise the link, they must be present in the `gtdb_rxx_web` database in the `gtdb_tree_yyy` table (where `xxx` is the release and `yyy` is the link type).

- Bergeys = `scripts/external/bergeys_update_links.py`
- LPSN = `scripts/external/lpsn_update_links.py`
- NCBI = `scripts/external/ncbi_update_links.py`
- SeqCode = `scripts/external/seqcode_update_links.py`

## Updating to a new GTDB release

There are a few steps involved in this process, it is not fully automated. The best way to do this is to compare the differences between previous releases:

- [R220 to R226](https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/compare/v2.20.4...v2.21.1)

### API updates

- In the `config.py` folder, the `GTDB_RELEASES` and `CURRENT_RELEASE` need to be updated.

### Database updates

**Taxon history:**

- Within the website database, the materialized view `taxon_history_mtview` needs to be updated so that the new release is included. It's very important to keep the last part of the crosstab query (the columns) in alphabetical order, i.e. the `AS ct(...)` part.
- This also requires an update in the `api/db/gtdb_web.py` file to reflect the new schema.

# api.gtdb.ecogenomic.org

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

This is done by running the following script within the context of the container:

```shell
cd /mnt/gtdb-website/repos/api.gtdb.ecogenomic.org
docker build -t ncbi-db -f docker/ncbi-db/Dockerfile .
nice docker run --rm --network gtdb-stack-config_default -e PYTHONPATH=/api -v /mnt/ncbi-genomes/ncbi:/mnt/ncbi-genomes/ncbi -it ncbi-db python scripts/update_fastani_db.py
```


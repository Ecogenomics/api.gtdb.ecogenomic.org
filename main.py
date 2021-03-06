# If running locally, load environment variables
if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from api import __version__
from api.config import Env, ENV_NAME
from api.view import fastani, taxonomy, species, taxon, sankey, search, genome, advanced, util, genomes, status, meta

# Documentation
tags_metadata = [
    {
        "name": "fastani",
        "description": "Perform ANI comparisons on RefSeq and GenBank genomes using [FastANI](https://github.com/ParBLiSS/FastANI).",
    },
    {
        "name": "taxonomy",
        "description": "Methods that generally group by a 7 rank taxonomy string.",
    },
    {
        "name": "species",
        "description": "Information about a species.",
    },
    {
        "name": "taxon",
        "description": "Information about a specific taxon.",
    },
    {
        "name": "sankey",
        "description": "Create a Sankey diagram from a search.",
    },
    {
        "name": "search",
        "description": "Search the GTDB.",
    },
    {
        "name": "genome",
        "description": "Information about a genome.",
    },
    {
        "name": "genomes",
        "description": "Information about genomes.",
    },
    {
        "name": "advanced",
        "description": "Advanced search API.",
    },
    {
        "name": "util",
        "description": "Utility methods.",
    },
    {
        "name": "meta",
        "description": "Methods that relate to the API.",
    },
]

# Initialise the app
app = FastAPI(title='GTDB API',
              version=__version__,
              docs_url='/',
              description=f'This API was designed for use by the GTDB website, however, you are free to use it for '
                          f'your own purposes. We will add more documentation in the future.<br><br>'
                          f'Most of the data available here can be downloaded as a flat file from the downloads page, '
                          f'please consider that before scraping.'
                          f'<ul>'
                          f'<li><a href="https://github.com/Ecogenomics/api.gtdb.ecogenomic.org" target="_blank">GitHub repository</a><br></li>'
                          f'<li><a href="https://github.com/Ecogenomics/api.gtdb.ecogenomic.org/blob/main/CHANGELOG.md" target="_blank">CHANGELOG</a></li>'
                          f'</ul>',
              openapi_tags=tags_metadata)

# Add routes
app.include_router(fastani.router)
app.include_router(species.router)
app.include_router(taxon.router)
app.include_router(taxonomy.router)
app.include_router(sankey.router)
app.include_router(search.router)
app.include_router(genome.router)
app.include_router(genomes.router)
app.include_router(advanced.router)
app.include_router(util.router)
app.include_router(status.router)
app.include_router(meta.router)

# Add CORS
if ENV_NAME is Env.LOCAL:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Static files
@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def v_favicon():
    return 'User-agent: *\nDisallow: /\n'


# https://github.com/tiangolo/fastapi/issues/1800#issuecomment-665825422
# # Setup the database
# @app.on_event("startup")
# async def startup():
#     await database.connect()
#
#
# @app.on_event("shutdown")
# async def shutdown():
#     await database.disconnect()
#


# If running locally
if __name__ == "__main__":
    uvicorn.run('main:app', host="0.0.0.0", port=9000, reload=True)

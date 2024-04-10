# If running locally, load environment variables
if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

import asyncio

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from api import __version__
from api.config import Env, ENV_NAME
from api.view import fastani, taxonomy, species, taxon, sankey, search, genome, advanced, util, genomes, status, meta, \
    sitemap, taxa

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
    {
        "name": "sitemap",
        "description": "Returns sitemap related data."
    },
    {
        "name": "taxa",
        "description": "Returns information about taxa."
    },
    {
        "name": "status",
        "description": "Returns information about the state of the web services."
    }
]

# Initialise the app
app = FastAPI(title='GTDB API',
              version=__version__,
              docs_url='/',
              description=f'<p>Although this API was initially created for use exclusively by the GTDB website, we welcome '
                          f'and encourage you to utilize it for your own purposes.</p>'
                          f'<p>We plan to expand our documentation in the near future to provide you with even more helpful information.</p>'
                          f'<p>It is important to note that a significant portion of the available data can be downloaded as a flat file from our downloads page, so we kindly ask that you consider this before resorting to scraping.</p>'
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
app.include_router(sitemap.router)
app.include_router(taxa.router)

# Add CORS
if ENV_NAME is Env.LOCAL:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    port = 9000
elif ENV_NAME is Env.PROD:
    port = 9000
elif ENV_NAME is Env.DEV:
    port = 9001
else:
    port = 9000


async def send_request_to_plausible(request: Request):
    # https://plausible.io/docs/custom-event-goals
    #
    try:
        if ENV_NAME is Env.PROD:
            domain = 'gtdb-api.ecogenomic.org'
        elif ENV_NAME is Env.DEV:
            domain = 'gtdb-api-dev.ecogenomic.org'
        else:
            print('Running local - skipping analytics.')
            return

        url = 'https://gtdb-stats.ecogenomic.org/api/event'
        user_agent = request.headers.get('user-agent')
        x_forwarded_for = request.headers.get('x-forwarded-for')

        if x_forwarded_for is None:
            print('Unable to determine IP address for plausible analytics.')
            return

        headers = {
            'User-Agent': user_agent,
            'X-Forwarded-For': x_forwarded_for,
            'Content-Type': 'application/json'
        }
        data = {
            'name': 'pageview',
            'url': f'https://{domain}{request.get("path", "")}',
            'domain': domain,
            'props': {
                'method': request.method
            }
        }
        httpx.post(url, headers=headers, json=data, timeout=2.0)
    except Exception as e:
        print(f'Unable to send to plausible: {e}')
    return


# This will be executed on each API call
@app.middleware("http")
async def intercept_http_request(request: Request, call_next):
    response, _ = await asyncio.gather(call_next(request), send_request_to_plausible(request))

    # For requests that provide a cacheKey, cache the response for 1 year
    if ENV_NAME is Env.PROD and 'Cache-Control' not in response.headers and 'cacheKey' in request.query_params:
        response.headers["Cache-Control"] = "max-age=31536000, must-revalidate, proxy-revalidate"
    return response


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
    uvicorn.run('main:app', host="0.0.0.0", port=port, reload=True)

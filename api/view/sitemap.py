from urllib.parse import quote

from fastapi import APIRouter

from api.config import SITEMAP_PAGES
from api.db import GtdbDbDep, GtdbWebDbDep
from api.util.collection import iter_batches
from api.view.genomes import v_get_genomes_all
from api.view.species import v_species_all
from api.view.taxa import v_get_all_taxa

router = APIRouter(prefix='/sitemap', tags=['sitemap'])

MAX_ITEMS = 4000


@router.get(
    '',
    summary='Generate the sitemap content for the GTDB website.'
)
async def gtdb(
        db: GtdbDbDep,
        db_web: GtdbWebDbDep
):
    out = dict()

    # Load the genome pages for the sitemap
    all_species = v_species_all(db)
    all_genomes = v_get_genomes_all(db)
    all_taxa = v_get_all_taxa(db_web)

    # Generate the species pages
    species_i = 0
    for species_batch in iter_batches(all_species, MAX_ITEMS):
        species_key = f'sitemap-species-{species_i}.xml'
        out[species_key] = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for species in species_batch:
            out[species_key].extend([
                '   <url>',
                f'      <loc>https://gtdb.ecogenomic.org/species?id={quote(species[3:])}</loc>',
                '   </url>'
            ])
        out[species_key].append('</urlset>')
        out[species_key] = '\n'.join(out[species_key])

        species_i += 1

    genome_i = 0
    for genome_batch in iter_batches(all_genomes, MAX_ITEMS):
        genome_key = f'sitemap-genome-{genome_i}.xml'
        out[genome_key] = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for genome in genome_batch:
            out[genome_key].extend([
                '   <url>',
                f'      <loc>https://gtdb.ecogenomic.org/genome?gid={quote(genome)}</loc>',
                '   </url>'
            ])
        out[genome_key].append('</urlset>')
        out[genome_key] = '\n'.join(out[genome_key])
        genome_i += 1

    taxa_i = 0
    for taxa_batch in iter_batches(all_taxa.taxa, MAX_ITEMS):
        taxa_key = f'sitemap-tree-{taxa_i}.xml'
        out[taxa_key] = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for taxon in taxa_batch:
            out[taxa_key].extend([
                '   <url>',
                f'      <loc>https://gtdb.ecogenomic.org/tree?r={quote(taxon)}</loc>',
                '   </url>'
            ])
        out[taxa_key].append('</urlset>')
        out[taxa_key] = '\n'.join(out[taxa_key])
        taxa_i += 1

    # Generate the sitemap file (general)
    out['sitemap-general.xml'] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for page in SITEMAP_PAGES:
        out['sitemap-general.xml'].extend([
            '   <url>',
            f'      <loc>https://gtdb.ecogenomic.org/{quote(page)}</loc>',
            '   </url>'
        ])
    out['sitemap-general.xml'].append('</urlset>')
    out['sitemap-general.xml'] = '\n'.join(out['sitemap-general.xml'])

    # Generate the index sitemap file
    out['sitemap.xml'] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        '   <sitemap>',
        f'      <loc>https://gtdb.ecogenomic.org/sitemap-general.xml</loc>',
        '   </sitemap>',
    ]
    for i in range(species_i):
        out['sitemap.xml'].extend([
            '   <sitemap>',
            f'      <loc>https://gtdb.ecogenomic.org/sitemap-species-{i}.xml</loc>',
            '   </sitemap>',
        ])
    for i in range(genome_i):
        out['sitemap.xml'].extend([
            '   <sitemap>',
            f'      <loc>https://gtdb.ecogenomic.org/sitemap-genome-{i}.xml</loc>',
            '   </sitemap>',
        ])
    for i in range(taxa_i):
        out['sitemap.xml'].extend([
            '   <sitemap>',
            f'      <loc>https://gtdb.ecogenomic.org/sitemap-tree-{i}.xml</loc>',
            '   </sitemap>',
        ])
    out['sitemap.xml'].append('</sitemapindex>')
    out['sitemap.xml'] = '\n'.join(out['sitemap.xml'])

    return out

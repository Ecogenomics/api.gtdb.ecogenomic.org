if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

import multiprocessing as mp
import re

import requests
import sqlalchemy as sa
from bs4 import BeautifulSoup
from sqlalchemy import insert
from tqdm import tqdm

from api.db import GtdbCommonSession
# from api.db.models import GtdbCommonLpsnHtml, GtdbCommonLpsnHtmlNotes, GtdbCommonLpsnHtmlChildTaxa, \
#     GtdbCommonLpsnHtmlSynonyms
from api.util.collection import iter_batches

RANKS = ('domain', 'phylum', 'class', 'order', 'family', 'genus', 'species')
CPUS = 10
BATCH_SIZE = 500

RE_NUM_CHILD_TAXA_CORRECT = re.compile(r'Number of child taxa with a validly published and correct name: (\d+)')
RE_NUM_CHILD_TAXA_SYNONYMS = re.compile(
    r'Number of child taxa with a validly published name, including synonyms: (\d+)')
RE_NUM_CHILD_TAXA_TOTAL = re.compile(r'Total number of child taxa: (\d+)')
RE_RECORD_NUMBER = re.compile(r'(\d+)')

LPSN_RANKS = {'domain', 'phylum', 'class', 'order', 'family', 'genus', 'species', 'subspecies',
              'division', 'infrakingdom', 'infraphylum', 'kingdom', 'subclass', 'subdivision', 'subdomain', 'subfamily',
              'subgenus', 'subkingdom', 'suborder', 'subphylum', 'superclass', 'superdivision', 'superphylum', 'tribe',
              'uncategorized'}


def read_from_rank(rank: str):
    re_rank_pages = re.compile(r'<a href="\/' + rank + r'\?page=(\w)">')

    # Do an initial request to get the number of pages
    r = requests.get(f'https://lpsn.dsmz.de/{rank}')

    if not r.ok:
        raise Exception(f'Failed to get page: {rank}')

    html = r.text.replace('\n', '').replace('\r', '')
    hits = re_rank_pages.findall(html)

    if len(hits) == 0 and rank != 'domain':
        raise Exception(f'No hits for {rank}')

    return set(hits)


def get_taxa_from_rank_page(job):
    rank, url = job
    re_taxa_from_page = re.compile(r'<a href="(\/' + rank + r'\/[^"]+)"')

    r = requests.get(url)

    if not r.ok:
        return url, None

    html = r.text.replace('\n', '').replace('\r', '')
    hits = [f'https://lpsn.dsmz.de{x}' for x in re_taxa_from_page.findall(html)]

    return url, set(hits)


def get_taxon_page(url):
    r = requests.get(url)

    if not r.ok:
        return url, None

    return url, r.text.replace('\n', '').replace('\r', '')


def get_urls_already_processed():
    db = GtdbCommonSession()
    try:
        query = sa.select([GtdbCommonLpsnHtml.url])
        results = db.execute(query).fetchall()
        return {x.url for x in results}
    finally:
        db.close()


def get_links_from_other_categories():
    r = requests.get('https://lpsn.dsmz.de/other-categories')

    if not r.ok:
        raise Exception('Failed to get page: other-categories')

    soup = BeautifulSoup(r.text, 'html.parser')

    rows = soup.find_all('tr')

    out = set()
    for row in rows:
        if row.text.strip().startswith('Name'):
            continue

        a = row.find_all('a')
        if len(a) != 1:
            raise ValueError(f'Expected 1 link, found {len(a)}')
        href = a[0].attrs['href']
        href = f'https://lpsn.dsmz.de{href}'
        out.add(href)
    return out


def populate_taxa_from_ranks():
    # Do a final pass where we look at each page to check for extra links to non-linked pages
    extra_urls = get_extra_linked_pages()

    # Get uncommonly used ranks
    urls_other = get_links_from_other_categories()

    urls_done = get_urls_already_processed()
    print(f'Found {len(urls_done):,} URLs already processed')

    # Get the number of pages to process for each rank
    rank_pages = dict()
    for rank in tqdm(RANKS):
        rank_pages[rank] = set()
        cur_rank_pages = read_from_rank(rank)
        rank_pages[rank].add(f'https://lpsn.dsmz.de/{rank}')
        if len(cur_rank_pages) > 0:
            for page in cur_rank_pages:
                rank_pages[rank].add(f'https://lpsn.dsmz.de/{rank}?page={page}')
    print(f'Found {len(rank_pages):,} ranks to process')

    # Get the taxa URLs from each page
    queue_taxa_urls = list()
    for rank, urls in rank_pages.items():
        for url in urls:
            queue_taxa_urls.append((rank, url))

    taxa_urls = set()
    with mp.Pool(processes=CPUS) as pool:
        for url, hits in list(
                tqdm(pool.imap_unordered(get_taxa_from_rank_page, queue_taxa_urls), total=len(queue_taxa_urls))):
            if hits is None:
                print(f'Failed to get taxa from {url}')
            else:
                taxa_urls.update(hits)
    taxa_urls -= urls_done
    print(f'Found {len(taxa_urls):,} taxa URLs to process')

    # Add in any extra URLs we found
    additional_urls_todo = extra_urls - urls_done
    print(f'Found {len(additional_urls_todo):,} additional URLs to process from content')
    taxa_urls.update(additional_urls_todo)

    # Add in any URLs from other categories
    urls_other_todo = urls_other - urls_done
    print(f'Found {len(urls_other_todo):,} URLs from other categories')
    taxa_urls.update(urls_other_todo)

    # For each of the taxon URLs found, get the HTML
    db = GtdbCommonSession()
    batches = list(iter_batches(sorted(taxa_urls), n=BATCH_SIZE))
    try:
        for batch_i, batch in enumerate(batches):
            print(f'Processing batch {batch_i:,} of {len(batches):,}')
            with mp.Pool(processes=CPUS) as pool:
                for url, result in list(tqdm(pool.imap_unordered(get_taxon_page, batch), total=len(batch))):
                    if result is None:
                        print(f'Failed to get {url}')
                    else:
                        stmt = insert(GtdbCommonLpsnHtml).values(url=url, html=result)
                        db.execute(stmt)
            db.commit()
    finally:
        db.close()

    return


def find_extra_urls_on_page(html):
    out = set()
    soup = BeautifulSoup(html, 'html.parser')
    for link in soup.find_all('a'):
        if link.has_attr('href'):
            href = link['href']
            href_split = href.split('/')
            if len(href_split) > 2 and href_split[1] in LPSN_RANKS:
                out.add(f'https://lpsn.dsmz.de{href}')
    return out


def get_extra_linked_pages():
    print('Loading additional URLs from HTML content in database')
    out = set()
    db = GtdbCommonSession()
    try:
        query = sa.select([GtdbCommonLpsnHtml.html])
        results = db.execute(query).fetchall()
        results = [x.html for x in results]
    finally:
        db.close()
    with mp.Pool(processes=CPUS) as pool:
        for result in list(tqdm(pool.imap_unordered(find_extra_urls_on_page, results), total=len(results))):
            out.update(result)
    return out


def get_html_data_for_existing_rows():
    print('Getting data for existing rows')
    db = GtdbCommonSession()
    try:
        query = sa.select([GtdbCommonLpsnHtml.id, GtdbCommonLpsnHtml.url, GtdbCommonLpsnHtml.html]). \
            where(GtdbCommonLpsnHtml.to_process == True).order_by(GtdbCommonLpsnHtml.id)
        # query = sa.select([GtdbCommonLpsnHtml.id, GtdbCommonLpsnHtml.url, GtdbCommonLpsnHtml.html]).where(GtdbCommonLpsnHtml.id==1240)
        results = db.execute(query).fetchall()
        return {x.id: (x.url, x.html) for x in results}
    finally:
        db.close()


def get_url_to_id_mapping():
    print('Loading URL to ID mapping')
    db = GtdbCommonSession()
    try:
        query = sa.select([GtdbCommonLpsnHtml.id, GtdbCommonLpsnHtml.url])
        results = db.execute(query).fetchall()
        return {x.url: x.id for x in results}
    finally:
        db.close()


class ResultDict:

    def __init__(self):
        self.data = dict()

    def as_row(self, row_id: int, d_url_to_id_mapping):

        out = {
            'notes': list(),
            'child_taxa': list(),
            'synonyms': list(),
            'main': None,
        }

        # Create the insert query for the notes
        notes = self.get_notes()
        if notes is not None:
            for note in notes:
                stmt = insert(GtdbCommonLpsnHtmlNotes).values(page_id=row_id, doi=note.get('doi'),
                                                              note=note.get('text'))
                out['notes'].append(stmt)

        # Create the insert query for the child taxa
        child_taxa = self.get_child_taxa()
        if child_taxa is not None:
            for child_taxon_url, d_child_taxon_result in child_taxa.items():
                stmt = insert(GtdbCommonLpsnHtmlChildTaxa).values(
                    parent_page_id=row_id,
                    child_page_id=d_url_to_id_mapping[child_taxon_url],
                    nomenclatural_status=d_child_taxon_result['nom_status'],
                    taxonomic_status=d_child_taxon_result['tax_status'],
                )
                out['child_taxa'].append(stmt)

        # Link the synonyms
        synonyms = self.get_synonyms()
        if synonyms is not None:
            for synonym_url, synonym_kind in synonyms.items():
                stmt = insert(GtdbCommonLpsnHtmlSynonyms).values(
                    page_id=row_id,
                    synonym_id=d_url_to_id_mapping[synonym_url],
                    kind=synonym_kind
                )
                out['synonyms'].append(stmt)

        # Create the main update query
        query = sa.update(GtdbCommonLpsnHtml).where(GtdbCommonLpsnHtml.id == row_id)
        query = query.values(to_process=False)
        query = query.values(name=self.get_name())
        query = query.values(category=self.get_category())
        query = query.values(proposed_as=self.get_proposed_as())
        query = query.values(etymology=self.get_etymology())
        query = query.values(original_publication=self.get_original_publication())
        query = query.values(original_publication_doi=self.get_original_publication_doi())
        query = query.values(nomenclatural_status=self.get_nomenclatural_status())

        d_subdivision = self.get_subdivision()
        if d_subdivision is not None:
            query = query.values(n_child_correct=d_subdivision['n_child_correct'])
            query = query.values(n_child_synonym=d_subdivision['n_child_synonym'])
            query = query.values(n_child_total=d_subdivision['n_child_total'])

        query = query.values(assigned_by=self.get_assigned_by())
        query = query.values(assigned_by_doi=self.get_assigned_by_doi())
        query = query.values(record_number=self.get_record_number())
        query = query.values(gender=self.get_gender())
        query = query.values(valid_publication=self.get_valid_publication())
        query = query.values(valid_publication_doi=self.get_valid_publication_doi())
        query = query.values(ijsem_list=self.get_ijsem_list())
        query = query.values(ijsem_list_doi=self.get_ijsem_list_doi())
        query = query.values(taxonomic_status=self.get_taxonomic_status())
        query = query.values(effective_publication=self.get_effective_publication())
        query = query.values(effective_publication_doi=self.get_effective_publication_doi())
        query = query.values(emendations=self.get_emendations())
        query = query.values(tygs=self.get_tygs())
        query = query.values(type_strain=self.get_type_strain())
        query = query.values(strain_info=self.get_strain_info())
        query = query.values(risk_group=self.get_risk_group())

        ssu_result = self.get_16s()
        if ssu_result is not None:
            query = query.values(ssu_ggdc=ssu_result.get('ggdc'))
            query = query.values(ssu_fasta=ssu_result.get('fasta'))
            query = query.values(ssu_ebi=ssu_result.get('ebi'))
            query = query.values(ssu_ncbi=ssu_result.get('ncbi'))
            query = query.values(ssu=ssu_result.get('ssu'))

        basonym = self.get_basonym()
        if basonym is not None:
            query = query.values(basonym=d_url_to_id_mapping[basonym])

        type_species = self.get_type_species()
        if type_species is not None:
            query = query.values(type_species=d_url_to_id_mapping[type_species])

        type_subgenus = self.get_type_subgenus()
        if type_subgenus is not None:
            query = query.values(type_subgenus=d_url_to_id_mapping[type_subgenus])

        type_class = self.get_type_class()
        if type_class is not None:
            query = query.values(type_class=d_url_to_id_mapping[type_class])

        type_order = self.get_type_order()
        if type_order is not None:
            query = query.values(type_order=d_url_to_id_mapping[type_order])

        type_genus = self.get_type_genus()
        if type_genus is not None:
            query = query.values(type_genus=d_url_to_id_mapping[type_genus])

        parent_taxon = self.get_parent_taxon()
        if parent_taxon is not None:
            query = query.values(parent_taxon=d_url_to_id_mapping[parent_taxon])

        out['main'] = query

        return out

    def add(self, key: str, obj):
        if key in self.data:
            print(f'Key already exists: {key}')
        self.data[key] = obj

    def get_name(self):
        if 'name' not in self.data:
            return None
        parent_text = self.data['name'].parent.text.strip()
        name = parent_text.replace('Name:', '').strip()
        if len(name) < 3:
            raise ValueError(f'Name is too short: {name}')
        return name

    def get_category(self):
        if 'category' not in self.data:
            return None
        parent_text = self.data['category'].parent.text.strip()
        out = parent_text.replace('Category:', '').strip()
        if len(out) < 3:
            raise ValueError(f'Category is too short: {out}')
        return out

    def get_proposed_as(self):
        if 'proposed_as' not in self.data:
            return None
        parent_text = self.data['proposed_as'].parent.text.strip()
        out = parent_text.replace('Proposed as:', '').strip()
        if len(out) < 3:
            raise ValueError(f'Proposed as is too short: {out}')
        return out

    def get_etymology(self):
        if 'etymology' not in self.data:
            return None
        parent_text = self.data['etymology'].parent.text.strip()
        out = parent_text.replace('Etymology:', '').strip()
        if len(out) < 3:
            raise ValueError(f'Etymology is too short: {out}')
        return out

    def get_original_publication(self):
        if 'original_publication' not in self.data:
            return None
        parent_text = self.data['original_publication'].parent.text.strip()
        out = parent_text.replace('Original publication:', '').strip()
        if len(out) < 3:
            raise ValueError(f'Original publication is too short: {out}')
        return out

    def get_original_publication_doi(self):
        if 'original_publication' not in self.data:
            return None
        publication_doi_hits = self.data['original_publication'].parent.find_all('a', class_='doi-link')
        if len(publication_doi_hits) == 1:
            out = publication_doi_hits[0].attrs['href'].strip()
            if len(out) < 3:
                raise ValueError(f'Original publication doi is too short: {out}')
            return out
        elif len(publication_doi_hits) > 1:
            raise ValueError(f'Found more than one doi link: {publication_doi_hits}')
        return None

    def get_nomenclatural_status(self):
        if 'nomenclatural_status' not in self.data:
            return None
        parent_text = self.data['nomenclatural_status'].parent.text.strip()
        out = parent_text.replace('Nomenclatural status:', '').strip()
        if len(out) < 3:
            raise ValueError(f'Nomenclatural status is too short: {out}')
        return out

    def get_notes(self):
        if 'notes' not in self.data:
            return None

        note_items = self.data['notes'].parent.find_all('ul')
        if len(note_items) == 0:
            raise ValueError('No note items found')

        notes = set()
        for note_item in note_items:
            doi_hit = note_item.find_all('a', class_='doi-link')
            if len(doi_hit) == 1:
                doi = doi_hit[0].attrs['href'].strip()
                if len(doi) < 3:
                    raise ValueError(f'DOI is too short: {doi}')
            else:
                doi = None
            note_text = note_item.text.strip().replace('   ', '')
            notes.add((note_text, doi))

        out = list()
        for cur_text, cur_doi in notes:
            out.append({'text': cur_text, 'doi': cur_doi})
        return out

    def get_subdivision(self):
        if 'subdivision' not in self.data:
            return None

        ancestor_spans = self.data['subdivision'].parent.parent.find_all('span')
        if len(ancestor_spans) == 0:
            raise ValueError('No ancestor spans found')

        out = dict()
        for span in ancestor_spans:
            span_text = span.text.strip()
            n_taxa_correct_hit = RE_NUM_CHILD_TAXA_CORRECT.match(span_text)
            n_taxa_synonym_hit = RE_NUM_CHILD_TAXA_SYNONYMS.match(span_text)
            n_taxa_total_hit = RE_NUM_CHILD_TAXA_TOTAL.match(span_text)

            if n_taxa_correct_hit:
                out['n_child_correct'] = int(n_taxa_correct_hit.group(1))
            elif n_taxa_synonym_hit:
                out['n_child_synonym'] = int(n_taxa_synonym_hit.group(1))
            elif n_taxa_total_hit:
                out['n_child_total'] = int(n_taxa_total_hit.group(1))

        if len(out) != 3:
            raise ValueError('No subdivision data found')

        return out

    def get_child_taxa(self):
        if 'child_taxa' not in self.data:
            return None

        table_rows = self.data['child_taxa'].parent.find_all('tr')
        if len(table_rows) == 0:
            raise ValueError('No table rows found')

        out = dict()
        for row in table_rows:
            if row.text.strip() == 'Name Nomenclatural status Taxonomic status':
                continue

            columns = row.find_all('td')
            if len(columns) != 3:
                raise ValueError(f'Expected 3 columns, found {len(columns):,}')
            name_col, status_col, tax_status_col = columns

            name_href = name_col.find_all('a')
            if len(name_href) != 1:
                raise ValueError(f'Expected 1 name href, found {len(name_href):,}')
            name_link = name_href[0].attrs['href']
            name_link = f'https://lpsn.dsmz.de{name_link}'
            status_text = status_col.text.strip()
            tax_status_text = tax_status_col.text.strip()

            if status_text == '':
                status_text = None
            if tax_status_text == '':
                tax_status_text = None

            if name_link in out:
                raise ValueError(f'Duplicate name link: {name_link}')
            out[name_link] = {'nom_status': status_text, 'tax_status': tax_status_text}

        if len(out) == 0:
            raise ValueError('No child taxa found')
        return out

    def get_parent_taxon(self):
        if 'parent_taxon' not in self.data:
            return None

        parent_text = self.data['parent_taxon'].parent.text.strip()
        parent_text = parent_text.replace('Parent taxon:', '').strip()
        if parent_text == 'None.':
            return None

        out = None
        for anchor in self.data['parent_taxon'].parent.find_all('a'):
            if 'helper' in anchor.attrs.get('class', list()):
                continue
            if out is None:
                out = anchor.attrs['href']
                out = f'https://lpsn.dsmz.de{out}'
            else:
                raise ValueError('Found more than one parent taxon')

        if out is None:
            raise ValueError('No parent taxon found')
        return out

    def get_assigned_by(self):
        if 'assigned_by' not in self.data:
            return None

        parent_text = self.data['assigned_by'].parent.text.strip()
        out = parent_text.replace('Assigned by:', '').strip()
        if len(out) < 3:
            raise ValueError(f'Assigned by is too short: {out}')
        return out

    def get_assigned_by_doi(self):
        if 'assigned_by' not in self.data:
            return None

        parent_a = self.data['assigned_by'].parent.find_all('a', class_='doi-link')
        if len(parent_a) == 1:
            out = parent_a[0].attrs['href'].strip()
            if len(out) < 3:
                raise ValueError(f'Assigned by DOI is too short: {out}')
            return out
        return None

    # def get_linking(self):
    #     if 'linking' not in self.data:
    #         return None
    #
    #     span_hits = self.data['linking'].parent.find_all('span', class_='text')
    #     if len(span_hits) == 0:
    #         print('???')
    #     return span_hits[0].text.strip()

    def get_record_number(self):
        if 'record_number' not in self.data:
            return None

        for sibling in self.data['record_number'].next_siblings:
            sibling_text = sibling.text.strip()
            re_hit = RE_RECORD_NUMBER.match(sibling_text)
            if re_hit:
                return int(re_hit.group(1))

        raise ValueError('No record number found')
        return

    def get_synonyms(self):
        if 'synonyms' not in self.data:
            return None

        out = dict()
        for row in self.data['synonyms'].parent.find_all('tr'):
            row_text = row.text.strip()
            if row_text == 'Name Kind':
                continue
            columns = row.find_all('td')
            if len(columns) != 2:
                raise ValueError(f'Expected 2 columns for synonyms, got {len(columns):,}')
            name_val, kind_val = columns
            name_anchor = name_val.find_all('a')
            if len(name_anchor) != 1:
                raise ValueError('No anchor found')

            name_link = name_anchor[0].attrs['href'].strip()
            name_link = f'https://lpsn.dsmz.de{name_link}'
            kind_value = kind_val.text.strip()

            if name_link in out:
                raise ValueError(f'Duplicate synonym: {name_link}')
            out[name_link] = kind_value

        if len(out) == 0:
            raise ValueError('No synonyms found')
        return out

    def get_type_genus(self):
        if 'type_genus' not in self.data:
            return None

        out = None
        for anchor in self.data['type_genus'].parent.find_all('a'):
            if 'helper' in anchor.attrs.get('class', list()):
                continue
            if out is None:
                out = anchor.attrs['href'].strip()
                out = f'https://lpsn.dsmz.de{out}'
            else:
                raise ValueError('Found more than one type genus')

        if out is None:
            raise ValueError('No type genus found')
        return out

    def get_gender(self):
        if 'gender' not in self.data:
            return None
        parent_text = self.data['gender'].parent.text.strip()
        out = parent_text.replace('Gender:', '').strip()
        if len(out) < 3:
            raise ValueError('Gender too short')
        return out

    def get_valid_publication(self):
        if 'valid_publication' not in self.data:
            return None
        parent_text = self.data['valid_publication'].parent.text.strip()
        out = parent_text.replace('Valid publication:', '').strip()
        if len(out) < 3:
            raise ValueError('Valid publication too short')
        return out

    def get_valid_publication_doi(self):
        if 'valid_publication' not in self.data:
            return None
        doi_hit = self.data['valid_publication'].parent.find_all('a', class_='doi-link')
        if len(doi_hit) == 1:
            return doi_hit[0].attrs['href'].strip()
        elif len(doi_hit) > 1:
            raise ValueError('Found more than one valid publication DOI')
        return None

    def get_ijsem_list(self):
        if 'ijsem_list' not in self.data:
            return None
        parent_text = self.data['ijsem_list'].parent.text.strip()
        out = parent_text.replace('IJSEM list:', '').strip()
        if len(out) < 3:
            raise ValueError('IJSEM list too short')
        return out

    def get_ijsem_list_doi(self):
        if 'ijsem_list' not in self.data:
            return None

        doi_hit = self.data['ijsem_list'].parent.find_all('a', class_='doi-link')
        if len(doi_hit) > 1:
            raise ValueError('Found more than one IJSEM list DOI')
        elif len(doi_hit) == 1:
            return doi_hit[0].attrs['href'].strip()

        return None

    def get_taxonomic_status(self):
        if 'taxonomic_status' not in self.data:
            return None
        parent_text = self.data['taxonomic_status'].parent.text.strip()
        out = parent_text.replace('Taxonomic status:', '').strip()
        if len(out) < 3:
            raise ValueError('Taxonomic status too short')
        return out

    def get_type_order(self):
        if 'type_order' not in self.data:
            return None

        out = None
        for anchor in self.data['type_order'].parent.find_all('a'):
            if 'helper' in anchor.attrs.get('class', list()):
                continue
            if out is None:
                out = anchor.attrs['href'].strip()
                out = f'https://lpsn.dsmz.de{out}'
            else:
                raise ValueError('Found more than one type order')

        if out is None:
            raise ValueError('No type order found')
        return out

    def get_type_class(self):
        if 'type_class' not in self.data:
            return None

        out = None
        for anchor in self.data['type_class'].parent.find_all('a'):
            if 'helper' in anchor.attrs.get('class', list()):
                continue
            if out is None:
                out = anchor.attrs['href']
                out = f'https://lpsn.dsmz.de{out}'
            else:
                raise ValueError('Found more than one type class')

        if out is None:
            raise ValueError('No type class found')
        return out

    def get_effective_publication(self):
        if 'effective_publication' not in self.data:
            return None

        parent_text = self.data['effective_publication'].parent.text.strip()
        out = parent_text.replace('Effective publication:', '').strip()
        if len(out) < 3:
            raise ValueError('Effective publication too short')
        return out

    def get_effective_publication_doi(self):
        if 'effective_publication' not in self.data:
            return None
        doi_hit = self.data['effective_publication'].parent.find_all('a', class_='doi-link')
        if len(doi_hit) == 1:
            return doi_hit[0].attrs['href'].strip()
        elif len(doi_hit) > 1:
            raise ValueError('Found more than one effective publication DOI')
        return None

    def get_emendations(self):
        if 'emendations' not in self.data:
            return None

        parent_text = self.data['emendations'].parent.text.strip()
        out = parent_text.replace('Emendations:', '').strip().replace('   ', '')
        if len(out) < 3:
            raise ValueError('Emendations too short')
        return out

    def get_type_subgenus(self):
        if 'type_subgenus' not in self.data:
            return None

        out = None
        for anchor in self.data['type_subgenus'].parent.find_all('a'):
            if 'helper' in anchor.attrs.get('class', list()):
                continue
            if out is None:
                out = anchor.attrs['href'].strip()
                out = f'https://lpsn.dsmz.de{out}'
            else:
                raise ValueError('Found more than one type subgenus')

        if out is None:
            raise ValueError('No type subgenus found')
        return out

    def get_type_species(self):
        if 'type_species' not in self.data:
            return None

        out = None
        for anchor in self.data['type_species'].parent.find_all('a'):
            if 'helper' in anchor.attrs.get('class', list()):
                continue
            if out is None:
                out = anchor.attrs['href'].strip()
                out = f'https://lpsn.dsmz.de{out}'
            else:
                raise ValueError('Found more than one type species')

        if out is None:
            raise ValueError('No type species found')
        return out

    def get_tygs(self):
        if 'tygs' not in self.data:
            return None

        out = None
        for anchor in self.data['tygs'].parent.find_all('a'):
            if anchor.attrs.get('href', '').startswith('https://tygs'):
                if out is None:
                    out = anchor.attrs['href'].strip()
                else:
                    raise ValueError('Found more than one TYGS link')

        if out is None:
            raise ValueError('No TYGS link found')
        return out

    def get_16s(self):
        if '16s' not in self.data:
            return None

        parent_text = self.data['16s'].parent.text.strip()
        ssu_text = parent_text.replace('16S rRNA gene:', '').replace('Analyse FASTA', '').strip()
        if ssu_text == '':
            ssu_text = None

        anchors = self.data['16s'].parent.find_all('a')
        if len(anchors) > 5:
            raise ValueError('Found more than 5 16S links')
        out = {
            'ssu': ssu_text,
        }
        for anchor in anchors:
            if anchor.attrs.get('href', '').startswith('https://ggdc'):
                if 'ggdc' not in out:
                    out['ggdc'] = anchor.attrs['href'].strip()
                else:
                    raise ValueError('Found more than one GGDC link')

            elif anchor.attrs.get('href', '').startswith('/fasta/'):
                if 'fasta' not in out:
                    out['fasta'] = f'https://lpsn.dsmz.de{anchor.attrs["href"].strip()}'
                else:
                    raise ValueError('Found more than one FASTA link')

            elif anchor.attrs.get('href', '').startswith('https://www.ebi'):
                if 'ebi' not in out:
                    out['ebi'] = anchor.attrs['href'].strip()
                else:
                    raise ValueError('Found more than one EBI link')

            elif anchor.attrs.get('href', '').startswith('https://www.ncbi'):
                if 'ncbi' not in out:
                    out['ncbi'] = anchor.attrs['href'].strip()
                else:
                    raise ValueError('Found more than one NCBI link')
        return out

    def get_type_strain(self):
        if 'type_strain' not in self.data:
            return None

        parent_text = self.data['type_strain'].parent.text.strip()
        out = parent_text.replace('Type strain:', '').strip()
        if out == '':
            raise ValueError('Type strain too short')

        return out

    def get_strain_info(self):
        if 'strain_info' not in self.data:
            return None

        anchors = self.data['strain_info'].parent.find_all('a')
        if len(anchors) != 2:
            raise ValueError('Found more than 2 strain info links')

        href = anchors[1].attrs['href'].strip()
        if len(href) < 3:
            raise ValueError('Strain info link too short')
        return href

    def get_risk_group(self):
        if 'risk_group' not in self.data:
            return None

        parent_text = self.data['risk_group'].parent.text.strip()
        out = parent_text.replace('Risk group:', '').strip()
        return int(out)

    def get_basonym(self):
        if 'basonym' not in self.data:
            return None

        anchors = self.data['basonym'].parent.find_all('a')
        if len(anchors) != 2:
            raise ValueError('Found more than 2 basonym links')
        href = anchors[1].attrs['href'].strip()
        if len(href) < 3:
            raise ValueError('Basonym link too short')
        return f'https://lpsn.dsmz.de{href}'


def get_categories_from_soup(soup):
    out = ResultDict()

    for anchor in soup.find_all('a', class_='helper'):

        parent_text = anchor.parent.text.strip()

        if parent_text.startswith('Name:'):
            out.add('name', anchor)

        elif parent_text.startswith('Category:'):
            out.add('category', anchor)

        elif parent_text.startswith('Proposed as:'):
            out.add('proposed_as', anchor)

        elif parent_text.startswith('Etymology:'):
            out.add('etymology', anchor)

        elif parent_text.startswith('Original publication:'):
            out.add('original_publication', anchor)

        elif parent_text.startswith('Nomenclatural status:'):
            out.add('nomenclatural_status', anchor)

        elif parent_text.startswith('Notes:'):
            out.add('notes', anchor)

        elif parent_text.startswith('Subdivision:'):
            out.add('subdivision', anchor)

        elif parent_text.startswith('Child taxa:'):
            out.add('child_taxa', anchor)

        elif parent_text.startswith('Parent taxon:'):
            out.add('parent_taxon', anchor)

        elif parent_text.startswith('Assigned by:'):
            out.add('assigned_by', anchor)

        elif parent_text.startswith('Linking:'):
            out.add('linking', anchor)

        elif len([x for x in anchor.next_siblings if x.text.strip().startswith('Record number:')]) == 1:
            out.add('record_number', anchor)

        elif parent_text.startswith('Synonyms:'):
            out.add('synonyms', anchor)

        elif parent_text.startswith('Type genus:'):
            out.add('type_genus', anchor)

        elif parent_text.startswith('Gender:'):
            out.add('gender', anchor)

        elif parent_text.startswith('Valid publication:'):
            out.add('valid_publication', anchor)

        elif parent_text.startswith('IJSEM list:'):
            out.add('ijsem_list', anchor)

        elif parent_text.startswith('Taxonomic status:'):
            out.add('taxonomic_status', anchor)

        elif parent_text.startswith('Type order:'):
            out.add('type_order', anchor)

        elif parent_text.startswith('Type class:'):
            out.add('type_class', anchor)

        elif parent_text.startswith('Effective publication:'):
            out.add('effective_publication', anchor)

        elif parent_text.startswith('Emendations:'):
            out.add('emendations', anchor)

        elif parent_text.startswith('Type subgenus:'):
            out.add('type_subgenus', anchor)

        elif parent_text.startswith('Type species:'):
            out.add('type_species', anchor)

        elif parent_text.startswith('Conduct genome-based taxonomy'):
            out.add('tygs', anchor)

        elif parent_text.startswith('16S rRNA gene:'):
            out.add('16s', anchor)

        elif parent_text.startswith('Type strain:'):
            out.add('type_strain', anchor)

        elif parent_text.startswith('See detailed strain information at'):
            out.add('strain_info', anchor)

        elif parent_text.startswith('Risk group:'):
            out.add('risk_group', anchor)

        elif parent_text.startswith('Basonym:'):
            out.add('basonym', anchor)

        else:
            raise ValueError('Unknown column!')

    return out


def parse_page(d_url_to_id_mapping, row_id, html):
    soup = BeautifulSoup(html, 'html.parser')
    categories = get_categories_from_soup(soup)

    return categories.as_row(row_id, d_url_to_id_mapping)


def parse_html():
    d_id_to_url_and_html = get_html_data_for_existing_rows()
    d_url_to_id_mapping = get_url_to_id_mapping()

    print('Processing HTML pages...')
    db = GtdbCommonSession()
    try:
        for row_id, (url, html) in tqdm(d_id_to_url_and_html.items(), smoothing=0.01):
            d_result = parse_page(d_url_to_id_mapping, row_id, html)

            # Add the notes
            for note in d_result['notes']:
                try:
                    db.execute(note)
                except Exception as e:
                    print(row_id, e)

            for child_taxon in d_result['child_taxa']:
                try:
                    db.execute(child_taxon)
                except Exception as e:
                    print(row_id, e)

            for synonym in d_result['synonyms']:
                try:
                    db.execute(synonym)
                except Exception as e:
                    print(row_id, e)

            # Add the main row
            db.execute(d_result['main'])

            db.commit()


    finally:
        db.close()

    return


def main():
    # populate_taxa_from_ranks()
    parse_html()

    return


if __name__ == '__main__':
    main()

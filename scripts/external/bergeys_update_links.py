
import argparse
from pathlib import Path
import sys
from bs4 import BeautifulSoup
import requests
import json
from tqdm import tqdm
import re
import time

"""
Follow the process below in order to update the Bergey's links.

1. Open a browser and navigate to https://onlinelibrary.wiley.com/browse/book/10.1002/9781118960608/toc
   
2. Save the page to disk (complete, not just HTML only).
   
3. Run the following JavaScript command in the developer console to request all sections:

(async function() {

  // Create the URL parameters for the requests
  const urlBase = "https://onlinelibrary.wiley.com/pb/widgets/mrwTocBrowse/listChapters";
  const urlParams = new URLSearchParams({
    doi: "10.1002/9781118960608",
    widgetId: "7d782ec7-3a7f-473d-b03f-723f6c50ea76",
    pbContext: "pbContext=;issue:issue:doi\:10.1002/9781118960608;csubtype:string:Reference Work;website:website:pericles;subPage:string:Browse MRW TOC;journal:journal:mrwseries;page:string:Book Page;ctype:string:Book Content;wgroup:string:Publication Websites;pageGroup:string:Publication Pages"
  });

  // Iterate over each section and request the data from the server
  const responses = [];
  const sections = document.getElementsByClassName("accordion__control");
  let progress = 0;
  const totalSections = sections.length;
  for (const section of sections) {
    
    if (progress % 5 === 0) {
      console.log("Progress: ", progress, " of ", totalSections);
    }
    
    const api = section.getAttribute("data-sectionheading");

    let curPageId = 0;
    let maxPageId = 1;

    while (curPageId < maxPageId) {
      
      // Create the request object
      const curUrl = new URL(urlBase);
      const curParams = new URLSearchParams(urlParams);
      curParams.set("sectionHeading", api);
      curParams.set("startPage", curPageId);
      curUrl.search = curParams.toString();

      // Generate the request and parse it
      const curResponse = await fetch(curUrl, {
        credentials: "include"
      });
      const curData = await curResponse.json();
      
      // Store the request
      responses.push({
        "id": api,
        "page": curPageId,
        "result": curData
      });
      
      // Set the target page number based on the response
      maxPageId = curData["search"]["numberOfPages"];
      curPageId++;
    }
    
    progress++;
  }
  
  console.log(JSON.stringify(responses));
  

}());

4. After the command has finished running, open the final message. Right click it, and save it to a file.

5. Additionally, run the following SQL script in the GTDB website database to generate a list of taxa:



"""


def read_bergeys_toc_page(bergeys_html: Path):
    with bergeys_html.open('r') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # Obtain each section
    sections = list(soup.find_all(class_='accordion__control'))

    # Collect the data-sectionHeading attribute
    d_section_to_name = dict()
    d_section_to_tag = dict()
    d_api_to_data = dict()
    for section in sections:
        api = section.attrs['data-sectionheading']
        sec_id = section.attrs['id']
        taxon = section.attrs['title']
        if sec_id in d_section_to_name:
            print(f'WARNING duplicate section ID: {sec_id}')
        if sec_id in d_section_to_tag:
            print(f'WARNING duplicate section ID: {sec_id}')
        d_section_to_name[sec_id] = taxon
        d_section_to_tag[sec_id] = api
        d_api_to_data[api] = (sec_id, taxon)

    return d_api_to_data, d_section_to_name, d_section_to_tag



def clean_taxon_name(taxon):

    # Remove any non A-Z characters from the start and end of the taxon name
    taxon = re.sub(r'[^A-z\s]', '', taxon)
    taxon = taxon.strip()

    starts_with_ignore = ('Full Text for ', 'Form- ')
    ends_with_ignore = (' nov', ' fam', ' ord', ' phy', ' class', ' gen', ' phyl')

    while True:
        changes_made = False
        for prefix in starts_with_ignore:
            if taxon.startswith(prefix):
                taxon = taxon[len(prefix):].strip()
                changes_made = True
        for suffix in ends_with_ignore:
            if taxon.endswith(suffix):
                taxon = taxon[:-len(suffix)].strip()
                changes_made = True
        taxon = taxon.strip()
        if not changes_made:
            break
    return taxon

def parse_xslt(text):
    soup = BeautifulSoup(text, 'html.parser')
    links = soup.find_all('a', href=True)
    full_texts = [x for x in links if x.text.strip() == 'Full text']
    out = dict()
    for link in full_texts:
        taxon = link.attrs['aria-label']
        taxon = clean_taxon_name(taxon)
        href = link.attrs['href']
        url = f"https://onlinelibrary.wiley.com{href}"
        if taxon in out:
            raise Exception("?")
        out[taxon] = url
    return out


def parse_requests_js_output(path_to_js_output: Path):
    with path_to_js_output.open('r') as f:
        data = json.loads(f.readline())
    out = dict()
    for item in data:
        out[item['id']] = {
            'page': item['page'],
            'url': parse_xslt(item['result']['search']['xslt']) if len(item['result']['search']['xslt'].strip()) > 0 else None
        }
    return out



def create_taxon_tree(d_api_to_data, d_section_to_name, d_section_to_tag):

    re_section = re.compile(r'(heading-level-\d+-\d+)')
    d_api_to_taxstring = dict()
    ranks = ('phylum', 'class', 'order', 'family', 'genus', 'species')

    for api, (section_id, taxon) in d_api_to_data.items():

        # Clean the section ID into segments
        segments = re_section.findall(section_id)
        segments[0] = f'book-subject-{segments[0]}'

        # Top-level
        cur_tax = list()
        for i in range(len(segments)):
            rank = ranks[i]
            segment = '-'.join(segments[0:i+1])
            taxon = d_section_to_name[segment]
            taxon = clean_taxon_name(taxon)
            cur_tax.append(f'{rank[0]}__{taxon}')

        d_api_to_taxstring[api] = ';'.join(cur_tax)

    return d_api_to_taxstring


def read_sql_dump(path: Path):
    out = dict()
    with path.open() as f:
        for line in f.readlines():
            gtdb_id, taxon, in_db = line.strip().split('\t')
            out[taxon] = (int(gtdb_id), int(in_db) == 1)
    return out


def exact_taxon_match(js_data, gtdb_taxa, d_api_to_taxstring):

    d_js_taxa_to_urls = dict()
    for api_key, d_data in js_data.items():
        url = d_data['url']
        if url is None:
            continue

        # Get the tax string for the API key (may not match the URLs)
        tax_string = d_api_to_taxstring.get(api_key)
        taxon = tax_string.split(';')[-1]
        cur_rank = taxon[0]
        ranks = ('d', 'p', 'c', 'o', 'f', 'g', 's')
        cur_rank_index = ranks.index(cur_rank)

        # Given that there may be multiple URLs present for a given API key, we want to get the URL for the taxon
        # that matches the js taxon. Then the other ranks are lower ranks (e.g. for a family, the rest are genera).
        for url_taxon, cur_url in url.items():
            if url_taxon.lower().startswith('incertae sedis'):
                continue
            if url_taxon == taxon[3:]:
                if taxon in d_js_taxa_to_urls:
                    print(f"WARNING: DUPLICATE TAXON {taxon}, URLs: {d_js_taxa_to_urls[taxon]}, {cur_url}")
                d_js_taxa_to_urls[taxon] = cur_url
            else:
                cur_key = f'{ranks[cur_rank_index + 1]}__{url_taxon}'
                if cur_key in d_js_taxa_to_urls:
                    print(f"WARNING: DUPLICATE TAXON {taxon}, URLs: {d_js_taxa_to_urls[taxon]}, {cur_url}")
                d_js_taxa_to_urls[cur_key] = cur_url

    # Match the results to the GTDB taxa
    already_in_db = 0
    no_hit = 0
    n_taxa = 0
    out = dict()
    for js_taxon, cur_url in d_js_taxa_to_urls.items():
        gtdb_hit = gtdb_taxa.get(js_taxon)
        n_taxa += 1
        if gtdb_hit:
            gtdb_id, in_db = gtdb_hit
            if not in_db:
                if js_taxon in out:
                    print('??')
                out[js_taxon] = (gtdb_id, cur_url)
            else:
                already_in_db += 1
        else:
            no_hit += 1

    print(f'Total taxa with URLs: {n_taxa:,}, already in DB: {already_in_db:,}, no hit: {no_hit:,}, to add: {len(out):,}')
    return out



def main(args):
    # Read arguments
    bergeys_html = Path(args.bergeys_html)
    js_output = Path(args.js_output)
    taxa_file = Path(args.taxa)
    output_dir = Path(args.output)

    # Generate output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'bergeys_links_to_update.tsv'


    # Check that the files exist
    if not bergeys_html.exists():
        print(f'Error: {bergeys_html} does not exist.')
        sys.exit(1)

    if not js_output.exists():
        print(f'Error: {js_output} does not exist.')
        sys.exit(1)


    # Parse the HTML file to extract section names and tags
    d_api_to_data, d_section_to_name, d_section_to_tag = read_bergeys_toc_page(bergeys_html)

    # Merge the data to create the tree
    d_api_to_taxstring = create_taxon_tree(d_api_to_data, d_section_to_name, d_section_to_tag)

    # Parse the JavaScript output
    js_data = parse_requests_js_output(js_output)

    # Read the GTDB taxa file
    gtdb_taxa = read_sql_dump(taxa_file)

    # Match the taxa
    matches = exact_taxon_match(js_data, gtdb_taxa, d_api_to_taxstring)

    # Write them to disk
    with output_file.open('w') as f:
        for taxon, (gtdb_id, url) in sorted(matches.items(), key=lambda x: x[0]):
            f.write(f'{gtdb_id}\t{url}\n')
    print(f'Wrote results to {output_file}')
    print('Import this into the "gtdb_tree_url_bergeys" table in the GTDB Common database.')
    print('Afterwards, run "CLUSTER gtdb_tree_url_bergeys"')

    return




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('bergeys_html', help='Path to the Bergeys HTML.')
    parser.add_argument("js_output", help="Path to the JavaScript output file containing all section requests.")
    parser.add_argument('taxa', help='Path to the GTDB taxa file.')
    parser.add_argument('output', help='Directory to output results.')
    main(parser.parse_args())

    """
    To generate the GTDB taxa file, use the following SQL command in the web database:

    select t.id, t.taxon, CASE WHEN s.id IS NULL THEN 0 else 1 END as in_db from gtdb_tree t
    LEFT JOIN gtdb_tree_url_seqcode s ON s.id = t.id
    where type in ('d', 'p', 'c', 'o', 'f', 'g', 's')
    """
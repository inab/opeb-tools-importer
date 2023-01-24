import argparse
import json
from matplotlib.font_manager import findfont
import requests
import os


from utils import get_url, connect_db, push_entry, save_entry, print_errors_log
from dotenv import load_dotenv

load_dotenv()


session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit 537.36 (KHTML, like Gecko) Chrome",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


def get_source(id_):
    string = id_.split('/')[5]
    source = string.split(':')[0]
    return(source)

def get_bioconda_biotools_galaxy_tools(tool, log):
    if tool['@id'].count('/')>5:
        source = get_source(tool['@id'])
        if source == 'biotools':
            tool['@data_source'] = 'biotools'
        elif source == 'bioconda':
            tool['@data_source'] = 'bioconda'
        elif source == 'galaxy':
            tool['@data_source'] = 'galaxy'

        tool['@source_url'] = tool['@id']
    else:
        log['canonical_N'] +=1

    return(tool, log)


def import_data():

    # 0. connect database/set output file
    print('Connecting to database')
    STORAGE_MODE = os.getenv('STORAGE_MODE', 'db')

    if STORAGE_MODE =='db':
        alambique = connect_db()

    else:
        OUTPUT_PATH = os.getenv('OUTPUT_PATH', './data/opebtools.json')


    # 1. Download all opeb
    print('Downloading OPEB tools')
    URL_OPEB_TOOLS = os.getenv('URL_OPEB_TOOLS', 'https://openebench.bsc.es/monitor/tool')
    print(f'OpenEBench tools URL: {URL_OPEB_TOOLS}')
    
    tools = get_url(URL_OPEB_TOOLS)
    print('Tools obtained')

    # 2. Get tools
    log = {'errors':[], 'n_ok':0, 'names': [],'canonical_N': 0}
    #For tool in OPEB Tool db
    for tool in tools:

        # 3. Process metadata
        tool, log = get_bioconda_biotools_galaxy_tools(tool,log)

        # 4. push to db/file
        if STORAGE_MODE=='db':
            log = push_entry(tool, alambique, log)

        else:
            log = save_entry(tool, OUTPUT_PATH, log)
     
    print(log)

    # Importation finished
    print(f'''\n----- OPEB Tools Importation finished -----
    Number of tools in OPEB {len(log['names'])}
    Number of canonical tools: {log['canonical_N']}''')
    
    print_errors_log(log)


if __name__ == '__main__':
    import_data()
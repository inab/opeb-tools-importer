import argparse
import os
import sys
import logging
from dotenv import load_dotenv


from utils import get_url, connect_db, push_entry, add_metadata_to_entry


def get_source(id_):
    string = id_.split('/')[5]
    source = string.split(':')[0]
    return(source)

def get_bioconda_biotools_galaxy_tools(tool):
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
        logging.info(f'canonical_tool {tool["name"]}')
        return None

    return(tool)


def import_data():
    try:
        # 0.1 Set up logging
        parser = argparse.ArgumentParser(
            description="Importer of OpenEBench tools from OpenEBench Tool API"
        )
        parser.add_argument(
            "--loglevel", "-l",
            help=("Set the logging level"),
            default="INFO",
        )

        args = parser.parse_args()
        numeric_level = getattr(logging, args.loglevel.upper())

        logging.basicConfig(level=numeric_level, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
        
        # 0.2 Load .env
        logging.info("state_importation - 1")


        # 1. connect database/set output file
        logging.info('Connecting to database')

        alambique = connect_db('alambique')

        # 2. Download all opeb
        logging.info('Downloading OPEB tools')
        URL_OPEB_TOOLS = os.getenv('URL_OPEB_TOOLS', 'https://openebench.bsc.es/monitor/tool')
        logging.info(f'OpenEBench tools URL: {URL_OPEB_TOOLS}')
        
        tools = get_url(URL_OPEB_TOOLS)
        if tools:
        
            logging.info('Tools obtained')
            # 3. Get tools
            logging.info(f'Processing {len(tools)} tools ...')
            #For tool in OPEB Tool db
            for tool in tools:       
                # 4. Process metadata
                tool = get_bioconda_biotools_galaxy_tools(tool)

                # only keep biotools 
                if tool['@data_source'] != 'biotools':
                    continue

                if tool:
                    type_ = tool['@type']
                    name = tool['@label']
                    version = tool['@version']
                    source = tool['@data_source']

                    identifier = f"{source}/{name}/{type_}/{version}"

                    entry = {
                        'data': tool,
                        '_id': identifier,
                        '@data_source': source
                    }

                    document_w_metadata = add_metadata_to_entry(identifier, entry, alambique)
                    push_entry(document_w_metadata, alambique)
            
        else:
            logging.exception("Exception occurred")
            logging.error('error - crucial_object_empty')
            logging.error('No content to processed. content_decoded is empty. Exiting...')
            logging.info("state_importation - 2")
            exit(1) 
        
    except Exception as e:
        logging.exception("Exception occurred")
        logging.error(f'error - {type(e).__name__}')
        logging.info("state_importation - 2")
        exit(1)

    else:
        logging.info("state_importation - 0")
    



if __name__ == '__main__':
    load_dotenv()
    import_data()
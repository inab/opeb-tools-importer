import json 
import os
import requests
import ssl
import logging

from pymongo import MongoClient

def push_entry(tool:dict, collection:'pymongo.collection.Collection', log:dict):
    '''Push tool to collection.

    tool: dictionary. Must have at least an '@id' key.
    collection: collection where the tool will be pushed.
    log : {'errors':[], 'n_ok':0, 'n_err':0, 'n_total':len(insts)}
    '''
    # Push to collection
    # date objects cause trouble and are prescindable
    if 'about' in tool.keys():
            tool['about'].pop('date', None)
    try:
        updateResult = collection.update_many({'@id':tool['@id']}, { '$set': tool }, upsert=True)
    except Exception as e:
        log['errors'].append({'file':tool,'error':e})
        logging.error(e)
        logging.error(f'Error saving {tool["name"]}')
        return(log)
    else:
        log['n_ok'] += 1
    finally:
        return(log)


def save_entry(tool, output_file, log):
    '''Save tool to file.

    tool: dictionary. Must have at least an '@id' key.
    output_file: file where the tool will be saved.
    log : {'errors':[], 'n_ok':0, 'n_err':0, 'n_total':len(insts)}
    '''
    # Push to file
    # date objects cause trouble and are prescindable

    if 'about' in tool.keys():
            tool['about'].pop('date', None)
    try:
        if os.path.isfile(output_file) is False:
            with open(output_file, 'w') as f:
                json.dump([tool], f)
        else:
            with open(output_file, 'r+') as outfile:
                data = json.load(outfile)
                data.append(tool)
                # Sets file's current position at offset.
                outfile.seek(0)
                json.dump(data, outfile)

    except Exception as e:
        log['errors'].append({'file':tool['name'],'error':e})
        logging.error(e)
        logging.error(f'Error saving {tool["name"]}')
        return(log)

    else:
        log['n_ok'] += 1
    finally:
        return(log)

def connect_db():
    '''Connect to MongoDB and return the database and collection objects.

    '''
    ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambique')
    HOST = os.getenv('HOST', 'localhost')
    PORT = os.getenv('PORT', 27017)
    DB = os.getenv('DB', 'observatory')
    
    client = MongoClient(HOST, int(PORT))
    alambique = client[DB][ALAMBIQUE]

    return alambique


# initializing session
session = requests.Session()
headers = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit 537.36 (KHTML, like Gecko) Chrome",
"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"}

def get_url(url, verb=False):
    '''
    Takes and url as an input and returns a json response
    '''
    ssl._create_default_https_context = ssl._create_unverified_context
    try:
        re = session.get(url, headers=headers, timeout=(10, 30))
    except:
        logging.error('Impossible to make the request')
        logging.error(f"Problematic url: {url}")
        return(None)
    else:
        if re.status_code == 200:
            content_decoded = decode_json(re)
            return(content_decoded)
        else:
            logging.error(f"Error while fetching the url. Status code: {str(re.status_code)}")
            logging.error(f"Problematic url: {url}")
            exit(1)


def decode_json(json_res):
    '''
    Decodes a json response
    '''
    try:
        content_decoded=json.loads(json_res.text)
    except:
        raise Exception(f'Could not decode opeb metrics JSON. Please, check URL_OPEB_METRICS')
    else:
        return(content_decoded)



import re
import ast
import uuid
import json
from src.azure_openai import OpenAIClient
from src.azure_translator import Translator
from src.azure_cosmos_db import AzureCosmos
from src.azure_blob import AzureBlob
from src.azure_form_recognizer import FormRecognizer
from src.azure_cognitive_search import CognitiveSearch
from src.chunking import Chunking
from src.config import FORM_RECOGNIZER_KEY, FORM_RECOGNIZER_URL
from src.config import TRANSLATOR_KEY, TRANSLATOR_ENDPOINT, TRANSLATOR_LOCATION
from src.config import COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DATABASE_NAME
from src.config import COGNITIVE_SEARCH_KEY, COGNITIVE_SEARCH_ENDPOINT, CHUNKED_INDEX_NAME
from src.config import STORAGE_ACCOUNT_NAME, STORAGE_ACCOUNT_KEY, STORAGE_ACCOUNT_ENDPOINT, STORAGE_ACCOUNT_CONNECTION_STRING, STORAGE_SOURCE_CONTAINER_NAME, STORAGE_TARGET_CONTAINER_NAME, STORAGE_JSON_CONTAINER_NAME, STORAGE_TARGET_CONTAINER_URL
from src.logger import logger

openai_obj = OpenAIClient()
translator = Translator(TRANSLATOR_KEY, TRANSLATOR_ENDPOINT, TRANSLATOR_LOCATION)
cosmos = AzureCosmos(COSMOS_ENDPOINT, COSMOS_KEY)
cognitive_search = CognitiveSearch(COGNITIVE_SEARCH_KEY, COGNITIVE_SEARCH_ENDPOINT)
blob_storage = AzureBlob(STORAGE_ACCOUNT_CONNECTION_STRING)
form_recognizer = FormRecognizer(FORM_RECOGNIZER_KEY, FORM_RECOGNIZER_URL)
chunking = Chunking()

def parse_output(resp):
    if('answer' in resp):
        pdf_name = resp['pdf_name']
        answer = resp['answer']

        answer = answer.replace('Context','data')
        answer = answer.replace('context','data')
        
        return {
            'pdf_name': pdf_name,
            'answer': answer
        }

    else:
        return {
            'pdf_name': " ",
            'answer': "I don't have information regarding it currently. Sorry for the inconvenience!"
        }

def decode_json(text):
    try:
        decoder = json.JSONDecoder()
        pos = 0
        json_objects = []

        while pos < len(text):
            try:
                obj, pos = decoder.raw_decode(text, 0)
                json_objects.append(obj)
            except json.JSONDecodeError:
                pos+=1

        return json_objects
    except Exception as e:
        print(e)
        return []

def get_json_output(resp):    
    try:
        resp = ast.literal_eval(resp)
        resp = parse_output(resp)
    except:
        res = decode_json(resp)
        if(res!=[] and type(res[0])==dict):
            resp = res[0]
            resp = parse_output(resp)
        else:
            pattern = fr'("answer"\s*:\s*")([^"]+)(")'
            fixed_json_string = re.sub(pattern, lambda m: m.group(1) + m.group(2).replace('\n', '\\n') + m.group(3), resp)

            res = decode_json(fixed_json_string)
            if(res!=[] and type(res[0])==dict):
                resp = res[0]
                resp = parse_output(resp)
            else:
                resp = {
                'pdf_name': " ",
                'answer':"I don't have information regarding it currently. Sorry for the inconvenience!"
            }
    if(resp['answer']=='Not Found'):
        resp['answer'] = "I don't have information regarding it currently. Sorry for the inconvenience!"
    return resp

def qna(query, conversation_id, model, query_language):
    logger.info(f'{conversation_id} - Detecting if query is really {query_language}!')
    detected_query_language=translator.detect_language(query, conversation_id)
    if detected_query_language!=query_language:
        logger.info(f'{conversation_id} - Detected query language is not same as typed query language!')
        return{'pdf_name': '',
               'answer': 'Query language not recognized, please type a valid query!'
               }
    else:
        logger.info(f'{conversation_id} - Translating query to English!')
        query=translator.query_translate(query, conversation_id, query_language, target_language='en')

        if query=='':
            logger.info(f'{conversation_id} - exponential backoff failed for Translate query. returning services crowded response.')
            return {'pdf_name':'',
                    'answer':'Our services are crowded at the moment. Please try after some time!',
                }

    logger.info(f'{conversation_id} - fetching conversation history from Cosmos!')
    pairs = list(cosmos.query_items(COSMOS_DATABASE_NAME, 'conversation-history', f"""SELECT TOP 1 c.Q, c.A FROM c
                                    WHERE c.conversation_id = '{conversation_id}'
                                    ORDER BY c._ts DESC"""))[::-1]
    logger.info(f'{conversation_id} - conversation history from cosmos fetched successfully!')

    if (len(pairs)>=1):
        rephrased_query = openai_obj.rephrased_query(query, pairs, model, conversation_id)
        if (rephrased_query == 'OpenAI Not Responding'):
            logger.info(f'{conversation_id} - exponential backoff failed for chat completion. returning services crowded response.')
            return {
                        'answer': 'Our services are crowded at the moment. Please try after some time!'
                    }
    else:
        rephrased_query = query

    logger.info(f'{conversation_id} - rephrased query: {rephrased_query}')

    query_vector=openai_obj.create_embedding(query, conversation_id)
    relevant_content = cognitive_search.get_context(query_vector, conversation_id)

    if (relevant_content==''):
        logger.info(f'{conversation_id} - exponential backoff failed for chat completion. returning services crowded response.')
        return {'pdf_name':'',
                'answer':'Our services are crowded at the moment. Please try after some time!',
                }
    
    messages=openai_obj.create_prompt(rephrased_query, relevant_content, model, conversation_id)
    resp = openai_obj.chat_completion_json_format(messages=messages, model=model, conversation_id=conversation_id)

    if(resp=='OpenAI Not Responding'):
        logger.info(f'{conversation_id} - exponential backoff failed for chat completion. returning services crowded response.')
        return {'pdf_name':[],
                'answer':'Our services are crowded the at the moment. Please try after some time!',
            }

    logger.info(f'{conversation_id} - parsing json output: {resp}')
    resp = get_json_output(resp)
    logger.info(f'{conversation_id} - parsed json output: {resp}')

    body = {'id':str(uuid.uuid4()),'conversation_id':conversation_id, 'Q':rephrased_query, 'A':resp, 'original_query':query}

    logger.info(f'{conversation_id} - uploading response to cosmos!')
    cosmos.upsert_item(COSMOS_DATABASE_NAME, 'conversation-history', body)
    logger.info(f'{conversation_id} - successfully uploaded response to cosmos!')

    logger.info(f'{conversation_id} - Translating processed response to {detected_query_language}')
    resp['answer']=translator.translate_response(resp['answer'], conversation_id, target_language=detected_query_language, source_language='en')
    if resp['answer']=='':
        logger.info(f'{conversation_id} - exponential backoff failed for Response Translate query. returning services crowded response.')
        return {'pdf_name':'',
                'answer':'Our services are crowded at the moment. Please try after some time!',
                }
    
    return resp

def upload_pdf(pdf_path, pdf_name, conversation_id):
    # assign unique id to pdf
    search_client = cognitive_search.get_search_client(CHUNKED_INDEX_NAME)
    results = search_client.search(search_text="*", select=["id"])
    ids = set(result["id"].split('_')[0] for result in results)

    id = uuid.uuid4().hex
    while id in ids:
        id = uuid.uuid4().hex
    
    # upload pdf to blob
    logger.info(f'{conversation_id} - uploading file {pdf_name}!')
    result = blob_storage.upload_blob(STORAGE_SOURCE_CONTAINER_NAME, pdf_path, pdf_name)
    if result == True:
        logger.info(f'{conversation_id} - successfully uploaded file {pdf_name}!')
    else:
        logger.info(f'{conversation_id} - failed uploading file {pdf_name}!')

    # Translate document
    blob_client = blob_storage.initialize_blob_client(STORAGE_SOURCE_CONTAINER_NAME, pdf_name)
    source_blob_url = blob_client.url

    logger.info(f'{conversation_id} - translating file {pdf_name} to english!')
    result = translator.translate_document(source_blob_url, STORAGE_TARGET_CONTAINER_URL)
    if result == False:
        logger.info(f'{conversation_id} - translation failed for file {pdf_name}!')
    logger.info(f'{conversation_id} - translation successful for file {pdf_name}!')

    # read blob content into bytes
    logger.info(f'{conversation_id} - reading file {pdf_name} from blob!')
    done, content = blob_storage.read_blob(STORAGE_TARGET_CONTAINER_NAME, pdf_name)
    if done and content != '':
        logger.info(f'{conversation_id} - successfully read blob {pdf_name} from storage!')
    elif done and content == '':
        logger.info(f'{conversation_id} - successfully read blob {pdf_name} from storage but content not found!')
    else:
        logger.info(f'{conversation_id} - failed to read blob {pdf_name}!')

    # calling form recognizer object to process bytes
    logger.info(f'{conversation_id} - calling form-recognizer on bytes from blob {pdf_name}!')
    pages = form_recognizer.extract_content_from_blob(content)
    logger.info(f'{conversation_id} - successfully processed bytes into pages for blob {pdf_name}!')

    # processing the content into JSON and chunking it
    pdf_json = {
                    'id': id,
                    'pdf_name': pdf_name,
                    'content': '\n\n'.join(pages).strip()  
                }
    
    logger.info(f'{conversation_id} - splitting text into chunks for file {pdf_name}!')
    text_splitter = chunking.get_text_splitter()
    contents = text_splitter.split_text(pdf_json['content'].replace('\n\n', '. ', 1))
    pdf_json['content'] = contents
    logger.info(f'{conversation_id} - chunking completed for file {pdf_name}!')
    
    # creating embeddings
    logger.info(f'{conversation_id} - creating embeddings for file {pdf_name}!')
    try:
        done, embedding = openai_obj.create_embedding_docs(pdf_json['content'])

        if (done):
            pdf_json['content_vector'] = embedding
            logger.info(f'{conversation_id} - embedding creation successful for file {pdf_name}!')
        else:
            print(pdf_name, 'failed')
    except Exception as ex:
        logger.info(f'{conversation_id} - embedding creation failed for file {pdf_name} due to {ex}!')

    # storing json in container
    json_content = json.dumps(pdf_json)
    blob_name = f"{pdf_name.split('.')[0]}.json"
    logger.info(f'{conversation_id} - uploading json content of file {blob_name} to container {STORAGE_JSON_CONTAINER_NAME}!')
    result=blob_storage.upload_json_blob(STORAGE_JSON_CONTAINER_NAME, blob_name, json_content)
    if result:
        ids.add(id)
        logger.info(f'{conversation_id} - successfully uploaded json content of file {blob_name} to container {STORAGE_JSON_CONTAINER_NAME}!')
    else:
        logger.info(f'{conversation_id} - failed uploading json content of file {blob_name} to container {STORAGE_JSON_CONTAINER_NAME}!')

    # index the content
    logger.info(f'{conversation_id} - indexing the file {blob_name}!')
    result = index_doc(blob_name, conversation_id)
    if result:
        logger.info(f'{conversation_id} - indexing successful for file {blob_name}!')
        return result

def index_doc(blob_name, conversation_id):
    done, content = blob_storage.read_blob(STORAGE_JSON_CONTAINER_NAME, blob_name)
    if done:
        pdf_json = json.load(content)
    else:
        logger.info(f'{conversation_id} - indexing failed for file {blob_name}!')
        return False
    
    res = []

    for i in range(len(pdf_json['content'])):
        a = pdf_json.copy()
        
        id = a['id']+f'_{i}'

        a['id'] = id
        a['content'] = pdf_json['content'][i]
        a['content_vector'] = pdf_json['content_vector'][i]

        res.append(a)

    try:
        cognitive_search.upload_documents(res, CHUNKED_INDEX_NAME, len(res))
        return True
    except Exception as ex:
        logger.info(f'{conversation_id} - indexing failed for file {blob_name} due to {ex}!')
        return False

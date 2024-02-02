import os
import requests
import uuid
import logging
import json
from azure.ai.translation.document import DocumentTranslationClient
from azure.core.credentials import AzureKeyCredential
from src.logger import logger

class Translator:
    def __init__(self, key, endpoint, location):
        self.key = key
        self.endpoint = endpoint
        self.location = location

    def translate_document(self, source_url, target_url):
        try:
            doc_translate_client = DocumentTranslationClient(self.endpoint, AzureKeyCredential(self.key))

            poller = doc_translate_client.begin_translation(source_url, target_url, 'en')
            result = poller.result()

            return result # Unclear about the result received
        except Exception as ex:
            print(f'translate_document() failed due to {ex}')
            return False


    def detect_language(self, query, conversation_id):
        try:
            path = '/detect'
            constructed_url = self.endpoint + path

            params = {
                'api-version': '3.0'
            }

            headers = {
                'Ocp-Apim-Subscription-Key': self.key,
                'Ocp-Apim-Subscription-Region': self.location,
                'Content-type': 'application/json',
                'X-ClientTraceId': str(uuid.uuid4())
            }

            body = [{
                'text': query
            }]

            request = requests.post(
                constructed_url, params=params, headers=headers, json=body)
            response = request.json()

            logger.info(f'{conversation_id} - Query language detected.')

            return response[0]['language']
        
        except Exception as ex:
            logger.error(f'{conversation_id} - Query language detection failed due to {ex}', exc_info=True)
            return ''

    def query_translate(self, query, conversation_id, source_language, target_language='en'):
        try:
            path = '/translate'
            constructed_url = self.endpoint + path

            params = {
                'api-version': '3.0',
                'from': source_language,
                'to': target_language
            }

            headers = {
                'Ocp-Apim-Subscription-Key': self.key,
                'Ocp-Apim-Subscription-Region': self.location,
                'Content-type': 'application/json',
                'X-ClientTraceId': str(uuid.uuid4())
            }

            body = [{
                'text': query
            }]

            request = requests.post(constructed_url, params=params, headers=headers, json=body)
            response = request.json()
            logger.info(f'{conversation_id} - Translation Done Successfully From {source_language} to {target_language}.')

            return response[0]['translations'][0]['text']
        except Exception as ex:
            logger.error(f'{conversation_id} - Query Translation failed due to {ex}', exc_info=True)
            return ''

    def translate_response(self, resp, conversation_id, target_language, source_language='en'):
        try:
            path = '/translate'
            constructed_url = self.endpoint + path

            params = {
                'api-version': '3.0',
                'from': source_language,
                'to': target_language
            }

            headers = {
                'Ocp-Apim-Subscription-Key': self.key,
                'Ocp-Apim-Subscription-Region': self.location,
                'Content-type': 'application/json',
                'X-ClientTraceId': str(uuid.uuid4())
            }

            body = [{
                'text': resp
            }]

            request = requests.post(constructed_url, params=params, headers=headers, json=body)
            response = request.json()
            logger.info(f'{conversation_id} - Response Translation Done Successfully From {source_language} to {target_language}.')

            return response[0]['translations'][0]['text']
        except Exception as ex:
            logger.error(f'{conversation_id} - Response Translation failed due to {ex}', exc_info=True)
            return ''
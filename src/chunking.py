import json
import os
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
import openai

class Chunking:
    def __init__(self, api_key, api_type, api_base, api_version):
        self.openai.api_key = api_key
        self.openai.api_type = api_type
        self.openai.api_base = api_base
        self.openai.api_version = api_version

    def tiktoken_len(self, text):
        encoding = tiktoken.encoding_for_model('gpt-3.5-turbo')
        tokens = encoding.encode(text, disallowed_special=())
        return len(tokens)
    
    def get_text_splitter(self):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100, length_function=self.tiktoken_len)
        return text_splitter  
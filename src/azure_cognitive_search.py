from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient 
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import SearchIndex
from azure.search.documents.indexes.models import (
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
)

class CognitiveSearch:
    def __init__(self, admin_key, endpoint):
        self.admin_key = admin_key
        self.endpoint = endpoint

    def get_admin_client(self, index_name):
        admin_client = SearchIndexClient(endpoint=self.endpoint, index_name=index_name, credential=AzureKeyCredential(self.admin_key))
        return admin_client
    
    def get_search_client(self, index_name):
        search_client = SearchClient(endpoint=self.endpoint, index_name=index_name, credential=AzureKeyCredential(self.admin_key))
        return search_client
    
    def create_index(self, index_name, fields, cors_options, suggester):
        index = SearchIndex(name=index_name, fields=fields, cors_options=cors_options, suggesters = suggester)
        admin_client=self.get_admin_client(index_name)

        try:
            result = admin_client.create_index(index)
            print('Index', result.name, 'created')
        except Exception as ex:
            print(ex)

    def upload_documents(self, data, index_name, batch_size):
        search_client = self.get_search_client(index_name)

        try:
            for i in range(0, len(data), batch_size):
                search_client.upload_documents(documents=data[i:i+batch_size])
        except Exception as ex:
            print(ex)

    def get_vector_search(self, name, kind, params):
        return VectorSearch(
            algorithm_configurations=[
                VectorSearchAlgorithmConfiguration(
                    name=name,
                    kind=kind,
                    hnsw_parameters=params,
                )
            ])   
    
    def create_vector_index(self, index_name, fields, cors_options, vector_search, semantic_settings):
        index = SearchIndex(
            name = index_name,
            fields = fields,
            cors_options = cors_options,
            vector_search = vector_search,
            semantic_settings = semantic_settings
        )

        admin_client = self.get_admin_client(index_name)

        try:
            result = admin_client.create_index(index)
            print('Vector Index', result.name, 'created')
        except Exception as ex:
            print(ex) 

    def get_context(self, query_vector, conversation_id):
        if (query_vector==[]):
            return ''

        search_client = self.get_search_client()
        results =  search_client.search(
            search_text=None,
            vector=query_vector,
            top_k=3,
            vector_fields="contentVector",
            select=['pdf_name', 'content'],
        )
        results=list(results)
        contents = []
        for result in results:
            content = f'''Content({result['pdf_name']}): ```{result['content'].replace('#','').replace('*','')}```'''
            contents.append(content)

        relevant_content = '\n##########\n'.join(contents)
        return relevant_content


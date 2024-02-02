from azure.cosmos import CosmosClient
from azure.cosmos.partition_key import PartitionKey

class AzureCosmos():
    def __init__(self, endpoint, key):
        self.COSMOS_HOST = endpoint
        self.COSMOS_MASTER_KEY = key
        self.client = CosmosClient(self.COSMOS_HOST, {'masterKey': self.COSMOS_MASTER_KEY})
        print("[INFO] Cosmos Client created")

    def create_database(self, database_name):
        try:
            self.client.create_database_if_not_exists(database_name)
            print("[INFO] database created")
        except Exception as e:
            print("Error create_database(): ", e)
    
    def create_container(self, database_name, container_name, partition_key):
        try:
            self.database = self.client.get_database_client(database_name)
            self.database.create_container_if_not_exists(id=container_name, 
                                                         partition_key=PartitionKey(path=f"/{partition_key}"))
            print("[INFO] container created")
        except Exception as e:
            print("Error create_container(): ", e)
            
    def initialize_cosmosdb(self, database_name, container_name):
        try:
            self.database = self.client.get_database_client(database_name)
            self.container = self.database.get_container_client(container_name)
            print("[INFO] cosmos client created")
        except Exception as e:
            print("Error initialize_cosmosdb(): ", e)

    def query_items(self, database_name, container_name, query):
        try:
            self.initialize_cosmosdb(database_name, container_name)
            results=self.container.query_items(query = query)
            return results
        except Exception as e:
            print("Error query_items(): ", e)
            return False
        
    def upsert_item(self, database_name, container_name, data):
        try:
            self.initialize_cosmosdb(database_name, container_name)
            response = self.container.upsert_item(body=data)
            print("Conversation uploaded to CosmosDB")
        except Exception as e:
            print("Error upsert_item(): ", e)

    def delete_all_items_in_partition(self, database_name, container_name, partition_key):
        try:
            self.initialize_cosmosdb(database_name, container_name)
            ids=[i['id'] for i in (self.container.query_items(f'''SELECT c.id FROM c where c.conversation_id='{partition_key}' '''))]
            for id in ids:
                self.container.delete_item(item=id, partition_key=partition_key)

        except Exception as e:
            print("Error delete_all_items_in_partition(): ", e)
            return False
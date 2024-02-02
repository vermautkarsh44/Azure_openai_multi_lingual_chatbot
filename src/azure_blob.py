import os
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, ContentSettings

class AzureBlob:
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            
    def initialize_blob_client(self, container_name, file_name):
        try:
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=file_name)
            return blob_client
        except Exception as e:
            print(f"Error in initialize_blob_client() while initializing blob client for {file_name} : {e}")


    def upload_blob(self, container_name, filepath, file_name):
        try:
            blob_client=self.initialize_blob_client(container_name, file_name)
            with open(os.path.join(filepath,file_name), "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            print(f"File {filepath} uploaded to Azure Blob successfully.")
            return True
        except Exception as e:
            print(f"Error in upload_blob() while uploading {filepath} : {e}")
            return False

    def upload_json_blob(self, container_name, file_name, json_content):
        try:
            blob_client=self.initialize_blob_client(container_name, file_name)
            blob_client.upload_blob(json_content, content_settings=ContentSettings(content_type='application/json'))
            print(f'file {file_name} successfully uploaded to {container_name}!')
        except Exception as e:
            print(f"Error in upload_json_blob() while uploading file {file_name} : {e}")
            return False

    def list_all_blobs_in_container(self, container_name):
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            blobs_list = container_client.list_blobs()
            listf = [i['name'] for i in blobs_list]
            return listf
        except Exception as e:
            print(f"Error in list_all_blobs_in_container() : {e}")
            return False

    def list_all_containers(self):
        try:
            containers = [container['name'] for container in self.blob_service_client.list_containers()]
            return containers
        except Exception as e:
            print(f"Error in list_all_containers() while listing all containers : {e}")
            return []
        
    def read_blob(self, container_name, blob_name):
        try:
            blob_client=self.initialize_blob_client(container_name, blob_name)
            content = blob_client.download_blob().content_as_bytes()
            return True, content
        except Exception as e:
            print(f"Error in read_blob() while reading a blob : {e}")
            return False

    def get_files_blob(self, container_name, blob_name):
        try:
            blob_client = self.initialize_blob_client(container_name, blob_name)
            downloader = blob_client.download_blob()
            blob_client.close()
            print("File Downloaded : get_files_blob() Ran Successfully")
            return downloader
        except Exception as e:
            print(f"Error in get_files_blob() : {e}")
            return False


    def is_file_present_inside_container(self,file_name, container_name):
        try:
            flag = False
            conatiner_files_list = self.list_all_blobs_in_container(container_name)
            if file_name in conatiner_files_list:
                flag = True
            return flag
        except Exception as e:
            print("Error in is_file_present_inside_container() : {e}")
            return False


    def delete_blob(self, container_name, file_name):
        try:
            blob_client = self.initialize_blob_client(container_name, file_name)
            blob_client.delete_blob()
            return "deleted succesfully"
        except Exception as e:
            print(f"Error in delete_blob() : {e}")
            return False
        
    def create_blob_container(self, container_name):
        try:
            container_client = self.blob_service_client.create_container(name=container_name)
        except Exception as e:
            print(f"Error in create_blob_container() : {e}")
            return False
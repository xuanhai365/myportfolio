import os
#from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import azure.search.documents.indexes as indexes
from azure.storage.blob import BlobServiceClient

class AzureSetup:
    def __init__(self):
        #load_dotenv(override=True)
        self.oai_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.oai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.search_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
        self.search_api = os.getenv("AZURE_SEARCH_API_KEY")
        self.storage_connect_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.credential = AzureKeyCredential(self.search_api)

    # Setup Azure OpenAI client
    def setup_openai_client(self, api_version="2024-02-01"):
        openai_client = AzureOpenAI(
            api_key = self.oai_key,
            api_version = api_version,
            azure_endpoint = self.oai_endpoint
            )
        return openai_client

    #Set up Azure Search client
    def setup_search_client(self, index_name="my-search-index"): 
        search_client = SearchClient(endpoint=self.search_endpoint, index_name=index_name, credential=self.credential)
        return search_client

    # Set up Search Index client
    def setup_search_index_client(self):
        index_client = indexes.SearchIndexClient(endpoint=self.search_endpoint, credential=self.credential)
        return index_client
    
    # Set up Search Indexer client
    def setup_search_indexer_client(self):
        indexer_client = indexes.SearchIndexerClient(endpoint=self.search_endpoint, credential=self.credential)
        return indexer_client
    
    # Set up Azure Blob Storage client
    def setup_blob_client(self): 
        blob_client = BlobServiceClient.from_connection_string(self.storage_connect_string)
        return blob_client
    
    # Set up Search Index
    def setup_search_index(self, index_client, index_name="my-search-index"):
        search_index = indexes.models.SearchIndex(
            name = index_name,
            fields = [indexes.models.SearchField(
                        name="chunk_id",
                        type=indexes.models.SearchFieldDataType.String,
                        key=True,
                        hidden=False,
                        filterable=True,
                        sortable=True,
                        facetable=False,
                        searchable=True,
                        analyzer_name="keyword"
                    ),
                    indexes.models.SearchField(
                        name="parent_id",
                        type=indexes.models.SearchFieldDataType.String,
                        hidden=False,
                        filterable=True,
                        sortable=True,
                        facetable=False,
                        searchable=True
                    ),
                    indexes.models.SearchField(
                        name="chunk",
                        type=indexes.models.SearchFieldDataType.String,
                        hidden=False,
                        filterable=False,
                        sortable=False,
                        facetable=False,
                        searchable=True
                    ),
                    indexes.models.SearchField(
                        name="title",
                        type=indexes.models.SearchFieldDataType.String,
                        hidden=False,
                        filterable=False,
                        sortable=False,
                        facetable=False,
                        searchable=True
                    ),
                    indexes.models.SearchField(
                        name="vector",
                        type=indexes.models.SearchFieldDataType.Collection(indexes.models.SearchFieldDataType.Single),
                        hidden=False,
                        filterable=False,
                        sortable=False,
                        facetable=False,
                        searchable=True,
                        vector_search_dimensions=1536,
                        vector_search_profile_name="my_search_profile"
                    )],
            vector_search = indexes.models.VectorSearch(
                algorithms = [
                    indexes.models.HnswAlgorithmConfiguration(
                        name = 'my_hnsw',
                        #kind = indexes.models.VectorSearchAlgorithmKind.HNSW,
                        #parameters = indexes.models.HnswParameters(metric = 'cosine')
                    )
                ],
                profiles = [
                    indexes.models.VectorSearchProfile(
                        name = 'my_search_profile',
                        algorithm_configuration_name = 'my_hnsw'
                    )
                ],
                #vectorizers=[  
                    #indexes.models.AzureOpenAIVectorizer(  
                        #name="myOpenAI",  
                        #kind="azureOpenAI",  
                        #azure_open_ai_parameters=indexes.models.AzureOpenAIParameters(  
                            #resource_uri=oai_endpoint,  
                            #deployment_id='text-embedding-ada-002',
                            #model_name='text-embedding-ada-002',
                            #api_key=oai_key,
                        #),
                    #),  
                #],  
            ),
            semantic_search = indexes.models.SemanticSearch(
                configurations = [
                    indexes.models.SemanticConfiguration(
                        name="my_semantic_config",
                        prioritized_fields=indexes.models.SemanticPrioritizedFields(
                            title_field=indexes.models.SemanticField(field_name="title"),
                            content_fields=[indexes.models.SemanticField(field_name="chunk")]
                        )
                    )
                ]
            )
        )
        index_client.create_or_update_index(search_index)
        print("Search Index {} updated".format(index_name))

    # Set up Data Source Connection for Indexer
    def setup_data_source_connection(self, 
                                     indexer_client, 
                                     connection_name="my-data-connection", 
                                     container_name="mycontainer"):
        indexer_data = indexes.models.SearchIndexerDataContainer(name = container_name)
        data_connection = indexes.models.SearchIndexerDataSourceConnection(
            name = connection_name,
            type = indexes.models.SearchIndexerDataSourceType.azure_blob,
            container = indexer_data,
            connection_string = self.storage_connect_string
        )
        indexer_client.create_or_update_data_source_connection(data_connection)
        print("Data Source Connection {} updated".format(connection_name))
        

    # Set up skillset for Indexer
    def setup_indexer_skillset(self, indexer_client, skillset_name='my-skillset', index_name="my-search-index"):
        split_skill = indexes.models.SplitSkill(
            name = "Split Skill",
            default_language_code="en",
            context = '/document',
            text_split_mode = 'pages',
            maximum_page_length = 1000,
            page_overlap_length = 10,
            inputs = [
                indexes.models.InputFieldMappingEntry(
                    name = 'text',
                    source = '/document/content'
                )
            ],
            outputs = [
                indexes.models.OutputFieldMappingEntry(
                    name = 'textItems',
                    target_name = 'pages'
                )
            ]
        )
        embedding_skill = indexes.models.AzureOpenAIEmbeddingSkill(
            name = "OpenAI Embedding Skill",
            context = '/document/pages/*',
            resource_uri = self.oai_endpoint,
            api_key = self.oai_key,
            deployment_id = 'text-embedding-ada-002',
            model_name = 'text-embedding-ada-002',
            dimensions = 1536,
            inputs = [
                indexes.models.InputFieldMappingEntry(
                    name = 'text',
                    source = '/document/pages/*'
                )
            ],
            outputs = [
                indexes.models.OutputFieldMappingEntry(
                    name = 'embedding',
                    target_name = 'vector'
                )
            ]
        )
        index_projections = indexes.models.SearchIndexerIndexProjections(  
                selectors=[  
                    indexes.models.SearchIndexerIndexProjectionSelector(  
                        target_index_name=index_name,  
                        parent_key_field_name="parent_id",  
                        source_context="/document/pages/*",  
                        mappings=[
                            indexes.models.InputFieldMappingEntry(name="chunk", source="/document/pages/*"),  
                            indexes.models.InputFieldMappingEntry(name="vector", source="/document/pages/*/vector"),
                            indexes.models.InputFieldMappingEntry(name="title", source="/document/metadata_storage_name")
                        ]
                    )
                ],  
                parameters=indexes.models.SearchIndexerIndexProjectionsParameters(  
                    projection_mode=indexes.models.IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS  
                )  
            )
        skillset = indexes.models.SearchIndexerSkillset(
            name = skillset_name,
            description = 'Skillset for OpenAI Embedding',
            skills = [split_skill, embedding_skill],
            index_projections = index_projections
        )
        indexer_client.create_or_update_skillset(skillset)
        print("Skillset {} updated".format(skillset_name))

    # Set up Indexer
    def setup_search_indexer(self, indexer_client, 
                             indexer_name="my-search-indexer", 
                             connection_name="my-data-connection", 
                             index_name="my-search-index", 
                             skillset_name="my-skillset"):
        search_indexer = indexes.models.SearchIndexer(
            name = indexer_name,
            description = "Indexer for my-search-index",
            data_source_name = connection_name,
            target_index_name = index_name,
            skillset_name = skillset_name,
            schedule = indexes.models.IndexingSchedule(interval = "PT5M"),
        )
        try:
            indexer_client.create_or_update_indexer(search_indexer)
            indexer_client.run_indexer(indexer_name)
        except:
            pass
        print("Indexer {} updated".format(indexer_name))

    def upload_files(self, blob_client, container_name, file_path='database'):
        for file_name in os.listdir(file_path):
            blob_obj = blob_client.get_blob_client(container=container_name, blob=file_name)
            with open(os.path.join(file_path, file_name), "rb") as data:
                try:
                    blob_obj.upload_blob(data)
                except:
                    pass

    def setup(self, index_name, indexer_name, connection_name, skillset_name, container_name, file_path='database'):
        index_client = self.setup_search_index_client()
        indexer_client = self.setup_search_indexer_client()
        blob_client = self.setup_blob_client()

        self.setup_search_index(index_client, index_name)
        try:
            blob_client.create_container(name=container_name)
        except:
            pass
        self.upload_files(blob_client, container_name, file_path)
        self.setup_data_source_connection(indexer_client, connection_name, container_name)
        self.setup_indexer_skillset(indexer_client, skillset_name, index_name)
        self.setup_search_indexer(indexer_client, indexer_name, connection_name, index_name, skillset_name)
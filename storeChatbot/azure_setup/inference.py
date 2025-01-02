from .load_env import AzureSetup
import azure.search.documents.models as models

class MyChatbot:
    def __init__(self):
        chatbot = AzureSetup()
        chatbot.setup(
            index_name='my-search-index',
            indexer_name='my-search-indexer',
            connection_name='my-data-connection',
            skillset_name='my-skillset',
            container_name='my-container'
        )
        self.embed_model = "text-embedding-ada-002"
        self.llm_model = "gpt-4o"
        self.search_client = chatbot.setup_search_client(index_name='my-search-index')
        self.openai_client = chatbot.setup_openai_client()
        
    def get_response(self, input_query):
        # Format the input query for the Search service
        emmbeddings = self.generate_embeddings(input_query, self.embed_model)
        vector_query = models.VectorizedQuery(vector=emmbeddings, k_nearest_neighbors=3, fields="vector")

        # Search for the most relevant documents based on the formatted query
        search_results = self.search_client.search(
            search_text=input_query, 
            vector_queries=[vector_query])
        
        docs = ''
        # Merge the chunks of the top search results into a single document
        for result in search_results:
            docs = docs + result['chunk'] + '\n'

        # Generate a response to the user query using the OpenAI chat model
        prompt = '''INSTRUCTIONS: Answer the question using the information in the document provided.\n
        QUESTION: {query}.\n
        DOCUMENT: {document}'''.format(query=input_query, document=docs)
        response = self.openai_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": "You are a HR manager at a tech company."},
                {"role": "user", "content": prompt}
            ]
        )
        #print(response)
        #print(response.model_dump_json(indent=2))
        return response.choices[0].message.content

    def generate_embeddings(self, text, model):
        # Generate embeddings for the provided text using the specified model
        embeddings_response = self.openai_client.embeddings.create(model=model, input=text)
        # Extract the embedding data from the response
        embedding = embeddings_response.data[0].embedding
        return embedding

import os
import pickle
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from app.core.config import settings
from ...embedding_models import embedding
from ...llms import llm


class NaiveRAGService:
    def __init__(self, application_id, persist_dir="./storage/naive_rag_storage", default_required_exts=None):
        """
        Initialize the NaiveRAG service with a storage directory for indexes.

        Args:
            application_id (str): The ID of the application.
            persist_dir (str): Directory to store index pickle files.
            default_required_exts (list): Default file extensions to include during indexing.
        """
        self.application_id = application_id
        self.persist_dir = persist_dir
        self.default_required_exts = default_required_exts or [".py", ".md"]  # Default extensions
        os.makedirs(self.persist_dir, exist_ok=True)  
        self.index_cache = {} 
        Settings.llm = llm
        self.index = None
        Settings.embed_model = embedding
        self.response_streaming = settings.response_streaming
        try:
            # Load or create the index during initialization
            self.index = self._load_or_create_index()
        except Exception as e:
            print(f"Failed to load or create index for application_id '{self.application_id}'. {e}")

    def _get_index_path(self):
        """
        Get the path to the pickle file for the given application ID.
        """
        return os.path.join(self.persist_dir, f"{self.application_id}_index.pkl")

    def _load_or_create_index(self):
        """
        Load an existing index for the application or create a new one if it doesn't exist.

        Returns:
            VectorStoreIndex: The loaded or newly created index.
        """
        index_pickle_path = self._get_index_path()
        input_dir = f"target_codebases/{self.application_id}"

        if os.path.exists(index_pickle_path):
            print(f"Loading existing index for application_id '{self.application_id}'...")
            with open(index_pickle_path, "rb") as f:
                index = pickle.load(f)
        else:
            print(f"Index not found for application_id '{self.application_id}'. Creating a new one...")
            documents = SimpleDirectoryReader(
                input_dir=input_dir,
                required_exts=self.default_required_exts,
                recursive=True,
            ).load_data()

            index = VectorStoreIndex.from_documents(documents=documents, show_progress=True)

            # Save the index to a pickle file
            with open(index_pickle_path, "wb") as f:
                pickle.dump(index, f)
            print(f"Index saved for application_id '{self.application_id}' at {index_pickle_path}")

        return index

    def query(self, query):
        """
        Process a query for the preloaded index.

        Args:
            query (str): The query to execute against the index.

        Returns:
            str: The response from the query engine.
        """
        query_engine = self.index.as_query_engine(streaming=self.response_streaming)
        response = query_engine.query(query)
        return response


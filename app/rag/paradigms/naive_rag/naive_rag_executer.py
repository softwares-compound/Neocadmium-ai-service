import os
import pickle
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from app.core.config import settings
from ...embedding_models import embedding
from ...llms import llm


class NaiveRAGService:
    def __init__(self, application_id, target_codebases_path=None, persist_dir=None, default_required_exts=None):
        """
        Initialize the NaiveRAG service with a storage directory for indexes.

        Args:
            application_id (str): The ID of the application.
            target_codebases_path (str, optional): Path to the target codebases directory.
            persist_dir (str, optional): Directory to store index pickle files.
            default_required_exts (list, optional): File extensions to include during indexing.
        """
        self.application_id = application_id

        # Set the base paths dynamically
        self.target_codebases_path = os.path.normpath(target_codebases_path or self.get_target_codebases_dir())
        self.persist_dir = os.path.normpath(persist_dir or os.path.join(self.target_codebases_path, "naive_rag_storage"))

        # Ensure directories exist
        os.makedirs(self.persist_dir, exist_ok=True)

        self.default_required_exts = default_required_exts or [".py", ".md"]  # Default file extensions

        # LLM & Embedding Settings
        Settings.llm = llm
        Settings.embed_model = embedding
        self.response_streaming = settings.response_streaming
        self.index = None  # Placeholder for the index

        try:
            # Load or create the index during initialization
            self.index = self._load_or_create_index()
        except Exception as e:
            print(f"Failed to load or create index for application_id '{self.application_id}': {e}")

    @staticmethod
    def get_target_codebases_dir():
        """
        Returns the base directory path for storing application codebases.
        - macOS/Linux → ~/Documents/Cadmium/target-codebases
        - Windows → C:\\Users\\YourUser\\Documents\\Cadmium\\target-codebases
        """
        base_dir = os.path.normpath(os.path.join(os.path.expanduser("~"), "Documents", "Cadmium", "target-codebases"))
        os.makedirs(base_dir, exist_ok=True)  # Ensure directory exists
        return base_dir

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
        input_dir = os.path.normpath(os.path.join(self.target_codebases_path, self.application_id))

        # Ensure the application directory exists before loading the index
        os.makedirs(input_dir, exist_ok=True)

        if os.path.exists(index_pickle_path):
            try:
                print(f"Loading existing index for application_id '{self.application_id}'...")
                with open(index_pickle_path, "rb") as f:
                    index = pickle.load(f)
                return index
            except Exception as e:
                print(f"Failed to load existing index for '{self.application_id}': {e}")
                print(f"Rebuilding index for application_id '{self.application_id}'...")

        print(f"Index not found for application_id '{self.application_id}'. Creating a new one...")

        # Load files from the application directory
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

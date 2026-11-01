"""The clients are created on first use, not at import: the old module needed four live API keys
and a network connection just to be imported."""

from cohere import ClientV2
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from openai import OpenAI
from pinecone import Pinecone
from pymongo import MongoClient
from pymongo.server_api import ServerApi

from .diseases import DiseaseStore
from .knowledge import Knowledge
from .ner import OpenAINer


class Services:
    def __init__(self, settings):
        self.settings = settings
        self._ner = self._knowledge = self._diseases = self._mongo = None

    def ner(self):
        if self._ner is None:
            s = self.settings
            s.require("openai_api_key", "openai_model")
            self._ner = OpenAINer(
                OpenAI(api_key=s.openai_api_key, timeout=s.openai_timeout), s.openai_model
            )
        return self._ner

    def knowledge(self):
        if self._knowledge is None:
            s = self.settings
            s.require("openai_api_key", "pinecone_api_key", "cohere_api_key", "cohere_rerank_model")
            options = {"model": s.embedding_model} if s.embedding_model else {}
            embeddings = OpenAIEmbeddings(api_key=s.openai_api_key, **options)
            index = Pinecone(api_key=s.pinecone_api_key).Index(s.pinecone_index_name)
            self._knowledge = Knowledge(
                PineconeVectorStore(index=index, embedding=embeddings),
                ClientV2(api_key=s.cohere_api_key),
                s.cohere_rerank_model,
            )
        return self._knowledge

    def diseases(self):
        if self._diseases is None:
            s = self.settings
            s.require("mongodb_uri")
            self._mongo = MongoClient(s.mongodb_uri, server_api=ServerApi("1"))
            collection = self._mongo[s.mongodb_database][s.mongodb_collection]
            self._diseases = DiseaseStore(collection, s.mongodb_search_index)
        return self._diseases

    def close(self):
        if self._mongo is not None:
            self._mongo.close()

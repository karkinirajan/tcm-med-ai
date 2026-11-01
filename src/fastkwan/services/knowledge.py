from dataclasses import dataclass


@dataclass(frozen=True)
class Ranked:
    text: str
    index: int  # position in the candidate list that was sent to the reranker
    score: float


class Knowledge:
    """Vector search in Pinecone followed by reranking with Cohere."""

    def __init__(self, vectorstore, cohere_client, rerank_model):
        self.vectorstore = vectorstore
        self.cohere = cohere_client
        self.rerank_model = rerank_model

    def search(self, query, namespace, k):
        documents = self.vectorstore.similarity_search(query=query, k=k, namespace=namespace)
        return [document.page_content for document in documents]

    def rerank(self, query, texts, top_n):
        """The ``top_n`` best of ``texts``. Cohere's current rerank answer carries only an index and
        a score (no document text), so the text is looked up by index here."""
        response = self.cohere.rerank(
            model=self.rerank_model, query=query, documents=texts, top_n=top_n
        )
        return [
            Ranked(text=texts[item.index], index=item.index, score=item.relevance_score)
            for item in response.results
        ]

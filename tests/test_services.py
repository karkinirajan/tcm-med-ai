import types

import pytest

from fastkwan import services as services_module
from fastkwan.config import NotConfigured, Settings
from fastkwan.prompts import NER_PROMPT
from fastkwan.services import Services
from fastkwan.services.diseases import DiseaseStore
from fastkwan.services.knowledge import Knowledge
from fastkwan.services.ner import OpenAINer


# ------------------------------------------------------------------------------------- NER
class FakeChat:
    def __init__(self, content):
        self.calls = []
        message = types.SimpleNamespace(content=content)
        self._response = types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])
        self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


def test_ner_sends_the_shared_prompt_and_the_text_and_strips_the_answer():
    client = FakeChat("  痰，咳嗽 \n")
    assert OpenAINer(client, "chat-model").extract("患者咳嗽两天") == "痰，咳嗽"
    call = client.calls[0]
    assert call["model"] == "chat-model"
    assert call["messages"] == [
        {"role": "system", "content": NER_PROMPT},
        {"role": "user", "content": "患者咳嗽两天"},
    ]


def test_an_empty_answer_is_an_empty_string():
    assert OpenAINer(FakeChat(None), "m").extract("x") == ""


# ------------------------------------------------------------------------------- knowledge
class FakeVectorStore:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def similarity_search(self, query, k, namespace):
        self.calls.append((query, k, namespace))
        return [types.SimpleNamespace(page_content=p) for p in self.pages]


class FakeCohere:
    def __init__(self, order):
        self.order, self.calls = order, []

    def rerank(self, **kwargs):
        self.calls.append(kwargs)
        results = [types.SimpleNamespace(index=i, relevance_score=s) for i, s in self.order]
        return types.SimpleNamespace(results=results)  # Cohere v2: no document text in the answer


def test_search_passes_the_query_namespace_and_count_and_returns_the_texts():
    store = FakeVectorStore(["a", "b"])
    assert Knowledge(store, None, "r").search("痰", "fangji", 50) == ["a", "b"]
    assert store.calls == [("痰", 50, "fangji")]


def test_rerank_looks_the_text_up_by_index_because_cohere_v2_returns_none():
    cohere = FakeCohere([(2, 0.9), (0, 0.4)])
    ranked = Knowledge(None, cohere, "rerank-model").rerank("q", ["zero", "one", "two"], 2)
    assert [(r.text, r.index, r.score) for r in ranked] == [("two", 2, 0.9), ("zero", 0, 0.4)]
    assert cohere.calls == [
        {"model": "rerank-model", "query": "q", "documents": ["zero", "one", "two"], "top_n": 2}
    ]


# ---------------------------------------------------------------------------------- diseases
class FakeCollection:
    def __init__(self, found):
        self.found, self.pipeline = found, None

    def aggregate(self, pipeline):
        self.pipeline = pipeline
        return iter(self.found)


def test_the_disease_search_is_an_autocomplete_on_the_name_limited_to_one():
    collection = FakeCollection([{"病名": "感冒", "预防与调摄": "休息"}])
    assert DiseaseStore(collection, "diseaseName").find("感") == {
        "病名": "感冒",
        "预防与调摄": "休息",
    }
    search, limit, project = collection.pipeline
    assert search["$search"] == {
        "index": "diseaseName",
        "autocomplete": {"query": "感", "path": "病名"},
    }
    assert limit == {"$limit": 1} and project["$project"] == {"_id": 0, "病名": 1, "预防与调摄": 1}


def test_an_unknown_disease_is_none():
    assert DiseaseStore(FakeCollection([]), "idx").find("nothing") is None


# ------------------------------------------------------------------------- the lazy factory
@pytest.fixture
def made(monkeypatch):
    """Replaces every SDK constructor, recording how it was called (they would reach the network)."""
    record = {}

    def fake(name):
        def build(*args, **kwargs):
            record.setdefault(name, []).append((args, kwargs))
            instance = types.SimpleNamespace(args=args, kwargs=kwargs, closed=False)
            instance.Index = lambda index_name: ("index", index_name)
            instance.close = lambda: setattr(instance, "closed", True)
            instance.__getitem__ = None
            return instance

        return build

    for name in ("OpenAI", "Pinecone", "OpenAIEmbeddings", "PineconeVectorStore", "ClientV2"):
        monkeypatch.setattr(services_module, name, fake(name))

    class FakeMongo:
        def __init__(self, uri, **kwargs):
            record.setdefault("MongoClient", []).append(((uri,), kwargs))
            self.closed = False

        def __getitem__(self, database):
            record["database"] = database
            return (
                {"coll": "collection"}
                if False
                else types.SimpleNamespace(__getitem__=None)
                if False
                else FakeDatabase(record)
            )

        def close(self):
            self.closed = True

    class FakeDatabase:
        def __init__(self, record):
            self.record = record

        def __getitem__(self, collection):
            self.record["collection"] = collection
            return "the-collection"

    monkeypatch.setattr(services_module, "MongoClient", FakeMongo)
    return record


def configured(**extra):
    base = dict(
        openai_api_key="sk-demo",
        openai_model="chat-model",
        pinecone_api_key="pc-demo",
        cohere_api_key="co-demo",
        cohere_rerank_model="rerank-model",
        mongodb_uri="mongodb://demo",
    )
    return Settings(**{**base, **extra})


def test_nothing_is_created_at_import_or_construction(made):
    Services(configured())
    assert made == {}


def test_each_service_reports_what_it_is_missing():
    with pytest.raises(NotConfigured) as caught:
        Services(Settings()).ner()
    assert caught.value.names == ["OPENAI_API_KEY", "OPENAI_MODEL"]
    with pytest.raises(NotConfigured) as caught:
        Services(Settings(openai_api_key="k")).knowledge()
    assert caught.value.names == ["PINECONE_API_KEY", "COHERE_API_KEY", "COHERE_RERANK_MODEL"]
    with pytest.raises(NotConfigured) as caught:
        Services(Settings()).diseases()
    assert caught.value.names == ["MONGODB_URI"]


def test_the_ner_client_gets_the_key_a_timeout_and_the_model(made):
    ner = Services(configured()).ner()
    assert ner.model == "chat-model"
    ((_, kwargs),) = made["OpenAI"]
    assert kwargs["api_key"] == "sk-demo" and kwargs["timeout"] > 0


def test_services_are_built_once(made):
    services = Services(configured())
    assert services.ner() is services.ner() and services.knowledge() is services.knowledge()
    assert len(made["OpenAI"]) == 1 and len(made["Pinecone"]) == 1


def test_the_embedding_model_is_only_passed_when_configured(made):
    Services(configured()).knowledge()
    assert "model" not in made["OpenAIEmbeddings"][0][1]  # LangChain's default: what the index uses
    made.clear()
    Services(configured(embedding_model="my-embeddings")).knowledge()
    assert made["OpenAIEmbeddings"][0][1]["model"] == "my-embeddings"


def test_pinecone_cohere_and_the_rerank_model_are_wired(made):
    knowledge = Services(configured(pinecone_index_name="my-index")).knowledge()
    assert made["Pinecone"][0][1] == {"api_key": "pc-demo"}
    assert made["PineconeVectorStore"][0][1]["index"] == ("index", "my-index")
    assert made["ClientV2"][0][1] == {"api_key": "co-demo"}
    assert knowledge.rerank_model == "rerank-model"


def test_mongo_uses_the_stable_api_and_the_configured_names_and_is_closed(made):
    services = Services(
        configured(mongodb_database="db1", mongodb_collection="coll1", mongodb_search_index="idx")
    )
    store = services.diseases()
    ((_, kwargs),) = made["MongoClient"]
    assert kwargs["server_api"].version == "1"
    assert (made["database"], made["collection"], store.search_index) == ("db1", "coll1", "idx")
    mongo = services._mongo
    services.close()
    assert mongo.closed is True


def test_closing_without_mongo_is_fine():
    Services(Settings()).close()

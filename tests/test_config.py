import pytest

from fastkwan.config import NotConfigured, Settings


def test_defaults_need_no_services_and_touch_nothing(monkeypatch):
    for name in ("OPENAI_API_KEY", "PINECONE_API_KEY", "COHERE_API_KEY", "MONGODB_URI", "API_KEY"):
        monkeypatch.delenv(name, raising=False)
    s = Settings()
    assert (
        s.openai_api_key
        == s.pinecone_api_key
        == s.cohere_api_key
        == s.mongodb_uri
        == s.api_key
        == ""
    )
    assert s.host == "127.0.0.1" and s.cors_origin_list == []
    assert (s.pinecone_index_name, s.syndromes_namespace, s.prescriptions_namespace) == (
        "evidgpt",
        "syndromes",
        "fangji",
    )
    assert (s.mongodb_database, s.mongodb_collection, s.mongodb_search_index) == (
        "cmedai",
        "教科书",
        "diseaseName",
    )
    assert (s.syndrome_candidates, s.prescription_candidates, s.rerank_top_n) == (30, 50, 5)
    assert s.openai_model == "" and s.cohere_rerank_model == ""  # no model names are assumed


def test_the_old_variable_names_still_work(monkeypatch):
    for name, value in {
        "OPENAI_API_KEY": "sk-x",
        "PINECONE_API_KEY": "pc-x",
        "COHERE_API_KEY": "co-x",
        "MONGODB_URI": "mongodb://example",
        "PINECONE_INDEX_NAME": "my-index",
    }.items():
        monkeypatch.setenv(name, value)
    s = Settings()
    assert (s.openai_api_key, s.pinecone_api_key, s.cohere_api_key) == ("sk-x", "pc-x", "co-x")
    assert (s.mongodb_uri, s.pinecone_index_name) == ("mongodb://example", "my-index")


def test_require_names_every_missing_variable_in_upper_case():
    with pytest.raises(NotConfigured) as caught:
        Settings().require("openai_api_key", "cohere_rerank_model")
    assert caught.value.names == ["OPENAI_API_KEY", "COHERE_RERANK_MODEL"]
    assert "OPENAI_API_KEY, COHERE_RERANK_MODEL" in str(caught.value)
    Settings(openai_api_key="k").require("openai_api_key")  # present: no error


def test_cors_origins_are_a_clean_list():
    assert Settings(cors_origins=" https://a.example , https://b.example ,").cors_origin_list == [
        "https://a.example",
        "https://b.example",
    ]

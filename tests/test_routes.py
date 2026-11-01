import logging

import pytest
from fastapi.testclient import TestClient

from fastkwan.config import NotConfigured
from fastkwan.main import create_app

from .conftest import FakeKnowledge, FakeNer, FakeServices


def test_root_and_health_are_open(client):
    assert client.get("/health").json() == {"status": "healthy"}
    body = client.get("/").json()
    assert body["docs"] == "/docs" and body["version"] == "1.0.0"


# ----------------------------------------------------------------------------------- /syndrome
def test_syndrome_extracts_symptoms_searches_reranks_and_reorders(make_client):
    client, fake = make_client()
    response = client.post("/syndrome", json={"query": "患者咳嗽两天"})
    assert response.status_code == 200
    assert fake.ner().calls == ["患者咳嗽两天"]
    # the symptoms the NER found (not the raw description) are what is searched and reranked
    assert fake.knowledge().searches == [("咳嗽，痰", "syndromes", 30)]
    query, texts, top_n = fake.knowledge().reranks[0]
    assert (query, top_n) == ("咳嗽，痰", 5) and len(texts) == 2
    result = response.json()["result"]
    assert result.startswith("證型: 痰濕證\n症狀: 痰")  # the reranker put this one first
    assert "證型: 風寒證\n症狀: 咳" in result


def test_syndrome_searches_with_the_description_when_no_symptom_is_recognised(make_client):
    fake = FakeServices(None, ner=FakeNer(answer=""))
    client, fake = make_client(fake)
    assert client.post("/syndrome", json={"query": "头晕"}).status_code == 200
    assert fake.knowledge().searches[0][0] == "头晕"


def test_syndrome_with_nothing_found_does_not_call_the_reranker(make_client):
    client, fake = make_client(FakeServices(None, knowledge=FakeKnowledge(texts=[])))
    response = client.post("/syndrome", json={"query": "x"})
    assert response.json() == {"result": "No matching syndromes found."}
    assert fake.knowledge().reranks == []


def test_candidate_counts_and_namespaces_come_from_the_settings(make_client):
    client, fake = make_client(syndromes_namespace="s-ns", syndrome_candidates=7, rerank_top_n=1)
    client.post("/syndrome", json={"query": "x"})
    assert fake.knowledge().searches == [("咳嗽，痰", "s-ns", 7)]
    assert fake.knowledge().reranks[0][2] == 1


# -------------------------------------------------------------------------------- /prescription
def test_prescription_uses_its_own_namespace_and_returns_ranked_items(make_client):
    client, fake = make_client()
    response = client.post("/prescription", json={"query": "咳嗽"})
    assert response.status_code == 200
    assert fake.knowledge().searches == [("咳嗽，痰", "fangji", 50)]
    body = response.json()
    assert body["results"][0] == {
        "text": "症狀: 痰 證型: 痰濕證 其他",
        "index": 1,
        "relevance_score": 0.9,
    }
    assert [item["index"] for item in body["results"]] == [1, 0]
    assert "message" not in body


def test_prescription_with_nothing_found(make_client):
    client, fake = make_client(FakeServices(None, knowledge=FakeKnowledge(texts=[])))
    response = client.post("/prescription", json={"query": "x"})
    assert response.json() == {"results": [], "message": "No matching prescriptions found"}
    assert fake.knowledge().reranks == []


# ---------------------------------------------------------------------------------- /lifestyle
def test_lifestyle_returns_the_disease(make_client):
    client, fake = make_client()
    response = client.post("/lifestyle", json={"query": "感冒"})
    assert response.status_code == 200
    assert response.json() == {"病名": "感冒", "预防与调摄": "多休息"}
    assert fake.diseases().calls == ["感冒"]


def test_lifestyle_unknown_disease_is_404(client):
    response = client.post("/lifestyle", json={"query": "nothing"})
    assert response.status_code == 404 and response.json() == {"detail": "Disease not found"}


# ------------------------------------------------------------------------------------- input
@pytest.mark.parametrize("path", ["/syndrome", "/prescription", "/lifestyle"])
@pytest.mark.parametrize("body", [{}, {"query": ""}, {"query": "x" * 4001}, {"query": 5}, None])
def test_bad_input_is_422_and_nothing_is_called(make_client, path, body):
    client, fake = make_client()
    response = client.post(path, json=body) if body is not None else client.post(path)
    assert response.status_code == 422
    assert (
        fake.ner().calls == [] and fake.knowledge().searches == [] and fake.diseases().calls == []
    )


# ------------------------------------------------------------------------------------ failures
class Exploding:
    def __init__(self, error):
        self.error = error

    def extract(self, text):
        raise self.error

    def search(self, *args):
        raise self.error

    def rerank(self, *args):
        raise self.error

    def find(self, name):
        raise self.error


def failing(**which):
    fake = FakeServices(None)
    for name, error in which.items():
        setattr(fake, f"_{name}", Exploding(error))
    return fake


@pytest.mark.parametrize(
    ("path", "which"),
    [
        ("/syndrome", "ner"),
        ("/syndrome", "knowledge"),
        ("/prescription", "ner"),
        ("/prescription", "knowledge"),
        ("/lifestyle", "diseases"),
    ],
)
def test_an_upstream_failure_is_a_502_that_does_not_leak_the_error(
    make_client, caplog, path, which
):
    secret = "401 invalid key sk-leaky-demo-value for https://internal.example"
    client, _ = make_client(failing(**{which: RuntimeError(secret)}))
    with caplog.at_level(logging.ERROR):
        response = client.post(path, json={"query": "x"})
    assert response.status_code == 502
    assert secret not in response.text and "sk-leaky" not in response.text
    assert "upstream service" in response.json()["detail"]
    assert "sk-leaky-demo-value" in caplog.text  # it is in the log, where the operator can see it


@pytest.mark.parametrize(
    ("path", "which", "names"),
    [
        ("/syndrome", "ner", ["OPENAI_API_KEY", "OPENAI_MODEL"]),
        ("/prescription", "knowledge", ["PINECONE_API_KEY"]),
        ("/lifestyle", "diseases", ["MONGODB_URI"]),
    ],
)
def test_a_missing_setting_is_a_503_naming_it(make_client, path, which, names):
    client, _ = make_client(failing(**{which: NotConfigured(names)}))
    response = client.post(path, json={"query": "x"})
    assert response.status_code == 503
    for name in names:
        assert name in response.json()["detail"]


# ------------------------------------------------------------------------------------ security
PROTECTED = ["/syndrome", "/prescription", "/lifestyle"]


@pytest.mark.parametrize("path", PROTECTED)
def test_with_an_api_key_set_calls_without_or_with_a_wrong_key_are_401(make_client, path):
    client, fake = make_client(api_key="demo-key")
    assert client.post(path, json={"query": "x"}).status_code == 401
    assert client.post(path, json={"query": "x"}, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post(path, json={"query": "x"}, headers={"X-API-Key": ""}).status_code == 401
    assert fake.ner().calls == [] and fake.diseases().calls == []  # nothing was spent


@pytest.mark.parametrize("path", PROTECTED)
def test_with_the_right_key_the_call_goes_through(make_client, path):
    client, _ = make_client(api_key="demo-key")
    response = client.post(path, json={"query": "感冒"}, headers={"X-API-Key": "demo-key"})
    assert response.status_code in (200, 404) and response.status_code != 401


def test_the_status_pages_stay_open_when_a_key_is_set(make_client):
    client, _ = make_client(api_key="demo-key")
    assert client.get("/health").status_code == 200 and client.get("/").status_code == 200


def test_without_an_api_key_set_the_service_is_open(client):
    assert client.post("/lifestyle", json={"query": "感冒"}).status_code == 200


# ---------------------------------------------------------------------------------------- CORS
def test_no_cors_headers_unless_origins_are_configured(client):
    response = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_cors_allows_only_the_configured_origins(make_client):
    client, _ = make_client(cors_origins="https://app.example")
    ok = client.get("/health", headers={"Origin": "https://app.example"})
    assert ok.headers["access-control-allow-origin"] == "https://app.example"
    other = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in other.headers


# ------------------------------------------------------------------------------------ lifecycle
def test_the_services_are_closed_on_shutdown(settings):
    fake = FakeServices(settings)
    with TestClient(create_app(settings, fake)) as client:
        client.get("/health")
        assert fake.closed == 0
    assert fake.closed == 1


def test_the_app_object_can_be_imported_without_any_configuration():
    from fastkwan.main import app

    assert app.title == "FastKwan"
    assert set(app.openapi()["paths"]) == {
        "/syndrome",
        "/lifestyle",
        "/prescription",
        "/health",
        "/",
    }


def test_run_serves_the_app_on_the_configured_host_and_port(monkeypatch):
    import fastkwan.main as main

    served = {}
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9123")
    monkeypatch.setattr(
        main.uvicorn, "run", lambda app, host, port: served.update(app=app, host=host, port=port)
    )
    main.run()
    assert (served["host"], served["port"]) == ("0.0.0.0", 9123)
    assert served["app"].title == "FastKwan"

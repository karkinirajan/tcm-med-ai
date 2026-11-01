import pytest

from fastkwan.config import Settings

# The tests must never read a developer's real .env.
Settings.model_config["env_file"] = None

from fastapi.testclient import TestClient  # noqa: E402

from fastkwan.main import create_app  # noqa: E402
from fastkwan.services.knowledge import Ranked  # noqa: E402


class FakeNer:
    def __init__(self, answer="咳嗽，痰"):
        self.answer, self.calls = answer, []

    def extract(self, text):
        self.calls.append(text)
        return self.answer


class FakeKnowledge:
    def __init__(self, texts=None):
        self.texts = (
            texts
            if texts is not None
            else ["症狀: 咳 證型: 風寒證 其他", "症狀: 痰 證型: 痰濕證 其他"]
        )
        self.searches, self.reranks = [], []

    def search(self, query, namespace, k):
        self.searches.append((query, namespace, k))
        return self.texts

    def rerank(self, query, texts, top_n):
        self.reranks.append((query, list(texts), top_n))
        return [Ranked(text=t, index=i, score=1 - i / 10) for i, t in enumerate(texts)][::-1][
            :top_n
        ]


class FakeDiseases:
    def __init__(self, table=None):
        self.table, self.calls = (
            table if table is not None else {"感冒": {"病名": "感冒", "预防与调摄": "多休息"}},
            [],
        )

    def find(self, name):
        self.calls.append(name)
        return self.table.get(name)


class FakeServices:
    def __init__(self, settings, ner=None, knowledge=None, diseases=None):
        self.settings = settings
        self._ner, self._knowledge, self._diseases = (
            ner or FakeNer(),
            knowledge or FakeKnowledge(),
            diseases or FakeDiseases(),
        )
        self.closed = 0

    def ner(self):
        return self._ner

    def knowledge(self):
        return self._knowledge

    def diseases(self):
        return self._diseases

    def close(self):
        self.closed += 1


@pytest.fixture
def settings():
    return Settings(rerank_top_n=5)


@pytest.fixture
def fakes(settings):
    return FakeServices(settings)


@pytest.fixture
def make_client(settings):
    def make(services=None, **overrides):
        effective = settings.model_copy(update=overrides)
        fake = services or FakeServices(effective)
        fake.settings = effective
        return TestClient(create_app(effective, fake)), fake

    return make


@pytest.fixture
def client(make_client):
    return make_client()[0]

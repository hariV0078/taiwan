import os

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters")

from app.models.listing import MaterialGrade
from app.services import classifier


class FakeStructured:
    def invoke(self, _messages):
        return classifier.ClassificationResult(
            material_category="Plastic/HDPE",
            grade=MaterialGrade.A1,
            confidence=0.92,
            needs_tpqc=False,
            is_blocked=False,
            block_reason=None,
            reasoning="High-purity HDPE",
        )


class FakeLLM:
    def __init__(self, *args, **kwargs):
        pass

    def with_structured_output(self, _schema):
        return FakeStructured()


def test_valid_material_returns_grade(monkeypatch):
    monkeypatch.setattr(classifier, "ChatOpenAI", FakeLLM)
    out = classifier.classify_material("Clean HDPE flakes", 1000, 95)
    assert out.grade == MaterialGrade.A1
    assert out.is_blocked is False


def test_restricted_material_blocked():
    out = classifier.classify_material("Contains asbestos fibers", 500, 70)
    assert out.is_blocked is True
    assert out.block_reason is not None


def test_banned_items_registry_blocks_pfoa_material():
    out = classifier.classify_material("PFOA-contaminated water treatment sludge", 250, 60)
    assert out.is_blocked is True
    assert out.block_reason is not None


def test_low_purity_low_grade(monkeypatch):
    class LowStructured:
        def invoke(self, _messages):
            return classifier.ClassificationResult(
                material_category="Mixed/Plastic Waste",
                grade=MaterialGrade.C,
                confidence=0.8,
                needs_tpqc=False,
                is_blocked=False,
                block_reason=None,
                reasoning="Low purity",
            )

    class LowLLM(FakeLLM):
        def with_structured_output(self, _schema):
            return LowStructured()

    monkeypatch.setattr(classifier, "ChatOpenAI", LowLLM)
    out = classifier.classify_material("Mixed dirty plastic", 2000, 30)
    assert out.grade == MaterialGrade.C


def test_confidence_sets_tpqc(monkeypatch):
    class LowConfidenceStructured:
        def invoke(self, _messages):
            return classifier.ClassificationResult(
                material_category="Metal/Steel",
                grade=MaterialGrade.B1,
                confidence=0.65,
                needs_tpqc=False,
                is_blocked=False,
                block_reason=None,
                reasoning="Uncertain",
            )

    class LowConfidenceLLM(FakeLLM):
        def with_structured_output(self, _schema):
            return LowConfidenceStructured()

    monkeypatch.setattr(classifier, "ChatOpenAI", LowConfidenceLLM)
    out = classifier.classify_material("Mixed steel turnings", 3000, 67)
    assert out.needs_tpqc is True

# tests/test_classify.py
import classify, config

def papers(n):
    return [{"id": f"arxiv:{i}", "title": f"T{i}", "abstract": f"A{i}",
             "categories": ["cs.LG"]} for i in range(n)]

def test_load_instruction():
    s = classify.load_instruction()
    assert "IN scope" in s and "operator-learning" in s and "USER MESSAGE" not in s

def test_build_message_numbers_papers():
    m = classify.build_message(papers(2))
    assert "[1]" in m and "[2]" in m and "T0" in m and "A1" in m

def test_classify_validates_and_drops_unknown_tags():
    def gen(instr, msg):
        return ('[{"id":1,"in_scope":true,"tags":["operator-learning","nope"],"reason":"r"},'
                '{"id":2,"in_scope":false,"tags":[],"reason":"out"}]')
    out, used = classify.classify(papers(2), gen, instruction="x", sleep=lambda s: None)
    assert out[0]["in_scope"] is True and out[0]["tags"] == ["operator-learning"]
    assert out[1]["in_scope"] is False and out[1]["tags"] == []
    assert used == 1

def test_classify_parses_fenced_and_wrapped_json():
    def gen(instr, msg):
        return '```json\n{"results": [{"id":1,"in_scope":true,"tags":[],"reason":"r"}]}\n```'
    out, _ = classify.classify(papers(1), gen, instruction="x", sleep=lambda s: None)
    assert len(out) == 1 and out[0]["in_scope"] is True

def test_classify_respects_cap(monkeypatch):
    monkeypatch.setattr(config, "BATCH_SIZE", 1)
    monkeypatch.setattr(config, "MAX_REQUESTS", 2)
    calls = {"n": 0}
    def gen(instr, msg):
        calls["n"] += 1
        return '[{"id":1,"in_scope":true,"tags":[],"reason":"r"}]'
    out, used = classify.classify(papers(5), gen, instruction="x", sleep=lambda s: None)
    assert calls["n"] == 2 and len(out) == 2 and used == 2

def test_classify_survives_bad_json():
    out, _ = classify.classify(papers(1), lambda i, m: "boom", instruction="x", sleep=lambda s: None)
    assert out == []

def test_classify_stops_on_balance_error():
    calls = {"n": 0}
    def gen(instr, msg):
        calls["n"] += 1
        raise RuntimeError("Error code: 402 - Insufficient Balance")
    out, used = classify.classify(papers(5), gen, instruction="x", sleep=lambda s: None)
    assert out == [] and calls["n"] == 1 and used == 0

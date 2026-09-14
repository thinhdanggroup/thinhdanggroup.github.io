import math

from script.daily_post.similarity import cosine, tfidf_vectors, tokenize, vector_for


def test_tokenize_lowercases_and_drops_punctuation():
    assert tokenize("From Kafka to NATS: Less Is More!") == [
        "from", "kafka", "to", "nats", "less", "is", "more",
    ]


def test_tokenize_drops_single_characters():
    assert "a" not in tokenize("a kafka broker")


def test_cosine_of_identical_vectors_is_one():
    v = {"kafka": 1.0, "nats": 2.0}
    assert math.isclose(cosine(v, v), 1.0, rel_tol=1e-9)


def test_cosine_of_disjoint_vectors_is_zero():
    assert cosine({"kafka": 1.0}, {"postgres": 1.0}) == 0.0


def test_cosine_of_empty_vector_is_zero_not_a_crash():
    assert cosine({}, {"kafka": 1.0}) == 0.0


def test_idf_penalises_terms_present_in_every_document():
    docs = ["kafka nats messaging", "kafka postgres indexes", "kafka python asyncio"]
    _, idf = tfidf_vectors(docs)
    assert idf["kafka"] < idf["nats"]


def test_vector_for_uses_supplied_idf():
    docs = ["kafka nats messaging", "kafka postgres indexes"]
    _, idf = tfidf_vectors(docs)
    v = vector_for("kafka messaging", idf)
    assert set(v) == {"kafka", "messaging"}
    assert v["messaging"] > v["kafka"]

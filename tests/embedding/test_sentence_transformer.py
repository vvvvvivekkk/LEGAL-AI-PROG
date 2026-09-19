import numpy as np

from src.embedding.sentence_transformer import embed


def test_embed_returns_2d_float_array(real_embedder):
    embedder = real_embedder
    vectors = embedder.embed(["hello world", "a different sentence"])
    assert vectors.shape[0] == 2
    assert vectors.dtype in (np.float32, np.float64)


def test_embed_empty_list_returns_empty_array(real_embedder):
    vectors = real_embedder.embed([])
    assert vectors.shape[0] == 0


def test_similar_sentences_are_closer_than_unrelated_ones(real_embedder):
    embedder = real_embedder
    anchor = embedder.embed(["The tenant must pay rent to the landlord."])[0]
    similar = embedder.embed(["A renter owes monthly payments to the property owner."])[0]
    unrelated = embedder.embed(["The chef baked a chocolate cake."])[0]

    sim_to_similar = float(np.dot(anchor, similar))
    sim_to_unrelated = float(np.dot(anchor, unrelated))
    assert sim_to_similar > sim_to_unrelated


def test_functional_embed_interface_matches_class(real_embedder):
    vectors = embed(["consistency check"])
    assert vectors.shape[0] == 1

import time

import pytest

from core.match import candidates, normalise_query, norm_salt, salt_key, same_strength


def test_normalise_query_strips_form_words():
    assert normalise_query("Dolo 650 Tablet") == "dolo 650"
    assert normalise_query("Augmentin 625 Duo Tab") == "augmentin 625 duo"


def test_salt_key_synonyms():
    assert norm_salt(" Amoxycillin ") == "amoxicillin"
    assert norm_salt("Acetaminophen") == "paracetamol"
    assert salt_key([{"salt": "paracetamol"}, {"salt": "Ibuprofen"}]) == "ibuprofen+paracetamol"


def test_same_strength():
    assert same_strength("650mg", "650 mg")
    assert same_strength("1 g", "1000mg")
    assert not same_strength("500mg", "650mg")


def test_contract_shape():
    c = candidates("Dolo 650")[0]
    assert set(c) == {"name", "base_name", "salts", "salt_key", "price", "pack", "desc", "score"}
    assert 0 <= c["score"] <= 100 and isinstance(c["price"], float)


@pytest.mark.parametrize("q,key", [
    ("Dolo 650", "paracetamol"),
    ("Combiflam", "ibuprofen+paracetamol"),
    ("Augmentin 625 Duo", "amoxicillin+clavulanic acid"),
    ("Telma-H", "hydrochlorothiazide+telmisartan"),
    ("Glycomet GP 1", "glimepiride+metformin"),
])
def test_known_brands(q, key):
    assert candidates(q)[0]["salt_key"] == key


def test_dolo_650_is_the_tablet():
    assert candidates("Dolo 650")[0]["name"] == "Dolo 650 Tablet"
    # strength passed separately still lands on the 650 tablet, not Dolo Drops
    assert candidates("Dolo", "650mg")[0]["name"] == "Dolo 650 Tablet"


def test_dedup_by_salt_key_and_k():
    cands = candidates("Celemax", k=5)
    keys = [c["salt_key"] for c in cands]
    assert len(keys) == len(set(keys)) == 5
    assert cands[0]["salt_key"] == "cefuroxime"
    assert [c["score"] for c in cands] == sorted([c["score"] for c in cands], reverse=True)


def test_empty_query():
    assert candidates("") == [] and candidates("tablet") == []


def test_latency_under_300ms():
    candidates("warm up")
    t = time.perf_counter()
    for q in ("Dolo 650", "Combiflam", "Celemax"):
        candidates(q)
    assert (time.perf_counter() - t) / 3 < 0.3


def test_bracketed_generic_and_form_and_brand_word():
    from core.match import candidates
    assert candidates("ATIVAN (Lorazepam)", "2mg", form="tablet")[0]["name"].startswith("Ativan")
    assert candidates("Rivotril (Clonazepam)", "0.5mg", form="tablet")[0]["name"].startswith("Rivotril")
    assert candidates("LEVOLIN", None, form="syrup")[0]["name"].startswith("Levolin ")
    assert "Suspension" in candidates("MEFTAL-P", "100/5", form="syrup")[0]["name"]


def test_written_suffix_word_is_respected():
    # R2-3: "Telma-H 40" must keep its HCTZ (a sulfa-allergy caution), not resolve to plain Telma 40.
    from core.match import candidates
    assert "hydrochlorothiazide" in candidates("Telma-H 40", None, form="tablet")[0]["salt_key"]

import pytest

from core.confidence import score


def cand(name, key, sc, strength="650mg"):
    return {"name": name, "base_name": name.lower(), "salts": [{"salt": s, "strength": strength} for s in key.split("+")],
            "salt_key": key, "price": 10.0, "pack": "strip of 10 tablets", "desc": "", "score": sc}


DOLO = cand("Dolo 650 Tablet", "paracetamol", 100)
FAR = cand("Spirodin 650 Tablet", "doxofylline", 80)
CELEMAX = cand("Celemax 500mg Tablet", "cefuroxime", 90, "500mg")
CALCIMAX = cand("Calcimax ISO Capsule", "calcitriol+calcium carbonate", 87, "500mg")


def test_clean_high():
    r = score({"strength": "650mg", "unsure": False}, [DOLO, FAR], "yes")
    assert r["band"] == "HIGH" and r["value"] == 1.0 and r["lasa_rival"] is None
    assert set(r["breakdown"]) == {"match", "gap_penalty", "unsure_penalty", "strength_penalty", "fit_adjust"}


def test_unsure_and_strength_penalties():
    r = score({"strength": "500mg", "unsure": True}, [DOLO, FAR], None)
    assert r["breakdown"]["unsure_penalty"] == -0.2 and r["breakdown"]["strength_penalty"] == -0.15
    assert abs(r["value"] - 0.65) < 1e-9 and r["band"] == "MEDIUM"


def test_fit_no_lowers():
    r = score({"strength": "650", "unsure": False}, [DOLO, FAR], "no")
    assert r["breakdown"]["fit_adjust"] == -0.2 and abs(r["value"] - 0.8) < 1e-9 and r["band"] == "MEDIUM"


def test_lasa_caps_at_medium():
    r = score({"brand_or_drug": "Celcimax", "strength": "500mg", "unsure": False}, [CELEMAX, CALCIMAX], "yes")
    # 0.9 + 0.1 - 0.15 = 0.85 would be HIGH, but a look-alike caps it at MEDIUM
    assert r["lasa_rival"]["name"] == "Calcimax ISO Capsule"
    assert r["breakdown"]["gap_penalty"] == -0.15 and r["band"] == "MEDIUM"
    assert any(x.startswith("Look-alike: Celemax 500mg Tablet (cefuroxime) vs Calcimax ISO Capsule") and "3 points apart" in x
               for x in r["reasons"])


def test_lasa_with_fit_no_is_low():
    r = score({"brand_or_drug": "Celcimax", "strength": "500mg", "unsure": False}, [CELEMAX, CALCIMAX], "no")
    assert r["band"] == "LOW" and r["lasa_rival"] is not None


def test_lasa_with_unsure_is_low():
    r = score({"brand_or_drug": "Celcimax", "strength": "500mg", "unsure": True}, [CELEMAX, CALCIMAX], None)
    assert r["band"] == "LOW"


def test_rival_outside_window_ignored():
    r = score({"strength": "650mg"}, [DOLO, cand("X", "doxofylline", 87.9)], None)
    assert r["lasa_rival"] is None and r["breakdown"]["gap_penalty"] == 0


def test_no_candidates_is_low():
    r = score({"strength": "650mg"}, [], None)
    assert r["band"] == "LOW" and r["value"] == 0 and r["reasons"]


def test_clamped():
    r = score({"strength": "9mg", "unsure": True}, [cand("Q", "a", 10), cand("R", "b", 5)], "no")
    assert r["value"] == 0.0 and r["band"] == "LOW"


def test_real_celemax_end_to_end():
    from core.match import candidates
    r = score({"brand_or_drug": "Celemax", "strength": "", "unsure": False}, candidates("Celemax"), "no")
    # exact read: Ceremax is 14 name-only points behind, so no rival; fit=no still keeps it off HIGH
    assert r["band"] == "MEDIUM" and r["lasa_rival"] is None
    r = score({"brand_or_drug": "Celemax", "strength": "", "unsure": True}, candidates("Celemax"), "no")
    assert r["band"] == "LOW"


# LASA name-only rule (coordinator fix): a shared strength number must not create a look-alike
SPIRODIN = {"name": "Spirodin 650 Tablet MR", "base_name": "spirodin 650 mr", "salts": [{"salt": "doxofylline", "strength": "650mg"}],
            "salt_key": "doxofylline", "price": 152.0, "pack": "strip of 10 tablets", "desc": "", "score": 92.0}
CELEMAX_500 = {"name": "Celemax 500mg Tablet", "base_name": "celemax 500mg", "salts": [{"salt": "cefuroxime", "strength": "500mg"}],
               "salt_key": "cefuroxime", "price": 260.0, "pack": "strip of 4 tablets", "desc": "", "score": 85.7}
CALCIMAX_ISO = {"name": "Calcimax ISO Capsule", "base_name": "calcimax iso",
                "salts": [{"salt": "calcium carbonate", "strength": "500mg"}, {"salt": "calcitriol", "strength": "0.25mcg"}],
                "salt_key": "calcitriol+calcium carbonate", "price": 380.0, "pack": "strip of 15 capsules", "desc": "", "score": 78.8}


def test_dolo_650_no_rival_from_shared_number():
    dolo = dict(DOLO, base_name="dolo 650")
    r = score({"brand_or_drug": "Dolo 650", "strength": "650mg", "unsure": False}, [dolo, SPIRODIN], None)
    assert r["lasa_rival"] is None and r["band"] == "HIGH"


def test_dolo_650_real_data_high():
    from core.match import candidates
    r = score({"brand_or_drug": "Dolo 650", "strength": "650mg", "unsure": False}, candidates("Dolo 650"), None)
    assert r["band"] == "HIGH" and r["lasa_rival"] is None


@pytest.mark.parametrize("read_name", ["Celcimax", "Calcemax"])
def test_celemax_calcimax_rival(read_name):
    r = score({"brand_or_drug": read_name, "strength": "500mg", "unsure": False}, [CELEMAX_500, CALCIMAX_ISO], None)
    assert r["lasa_rival"] is not None and r["lasa_rival"]["name"] == "Calcimax ISO Capsule"
    assert r["band"] in ("MEDIUM", "LOW")
    r2 = score({"brand_or_drug": read_name, "strength": "500mg", "unsure": False}, [CELEMAX_500, CALCIMAX_ISO], "no")
    assert r2["band"] == "LOW"


def test_substring_brand_is_not_a_lookalike():
    # "Doloral P" contains "Dolo" but is a different-looking name; an exact Dolo 650 read stays HIGH.
    from core.match import candidates
    read = {"brand_or_drug": "Dolo 650", "strength": "650 mg", "unsure": False}
    s = score(read, candidates("Dolo 650", "650 mg"), None)
    assert s["band"] == "HIGH" and s["lasa_rival"] is None


def test_calcimax_keeps_real_lookalike():
    # Calcimate-CL (calcitonin nasal spray) is a genuine different-salt look-alike of Calcimax.
    from core.match import candidates
    read = {"brand_or_drug": "Calcimax", "strength": None, "unsure": False}
    s = score(read, candidates("Calcimax"), "yes")
    assert s["band"] == "MEDIUM" and s["lasa_rival"] is not None


def test_one_shared_word_is_not_high():
    # Real case from the 15-prescription run: "B-plex fort" (vitamin B) matched B Cillin CV Forte (an antibiotic).
    from core.match import candidates
    read = {"brand_or_drug": "B-plex fort", "strength": None, "unsure": False}
    assert score(read, candidates("B-plex fort", None, form="tablet"), None)["band"] == "LOW"
    read = {"brand_or_drug": "ATIVAN (Lorazepam)", "strength": "2mg", "unsure": False}
    assert score(read, candidates("ATIVAN (Lorazepam)", "2mg", form="tablet"), None)["band"] == "HIGH"


def test_fit_yes_cannot_promote_to_high():
    read = {"strength": None, "unsure": False}
    near = dict(DOLO, score=80.0)  # 0.80 alone is MEDIUM; +0.10 for fit must not make it HIGH
    assert score(read, [near], "yes")["band"] == "MEDIUM"

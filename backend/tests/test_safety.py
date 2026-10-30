from core.safety import allergy, duplicates, jan_aushadhi, monthly_savings, schedule, strip_check

DOLO = {"label": "Dolo 650 Tablet", "salts": [{"salt": "paracetamol", "strength": "650mg"}], "freq": "TDS",
        "price": 34.27, "pack": "strip of 15 tablets"}
COMBI = {"label": "Combiflam Tablet", "salts": [{"salt": "Ibuprofen", "strength": "400mg"},
                                                {"salt": " paracetamol ", "strength": "325 mg"}], "freq": "BD"}
AUG = {"label": "Augmentin 625 Duo Tablet", "salts": [{"salt": "amoxycillin", "strength": "500mg"},
                                                      {"salt": "clavulanic acid", "strength": "125mg"}], "freq": "1 tab BD after food",
       "price": 223.42, "pack": "strip of 10 tablets"}
CEF = {"label": "Celemax 500mg Tablet", "salts": [{"salt": "cefuroxime", "strength": "500mg"}], "freq": "BD"}
TELMA_H = {"label": "Telma H Tablet", "salts": [{"salt": "telmisartan", "strength": "40mg"},
                                               {"salt": "hydrochlorothiazide", "strength": "12.5mg"}], "freq": "OD"}
ATORVA = {"label": "Atorva 20 Tablet", "salts": [{"salt": "atorvastatin", "strength": "20mg"}], "freq": "HS"}


# SAFE-1 duplicates
def test_duplicate_paracetamol_sums_mg():
    al = duplicates([DOLO, COMBI])
    assert len(al) == 1
    a = al[0]
    assert a["severity"] == "HIGH" and a["type"] == "DUPLICATE" and a["meds"] == [0, 1]
    assert "Paracetamol in Dolo 650 Tablet (650mg) and Combiflam Tablet (325 mg) = 975 mg per combined dose" in a["detail"]


def test_no_duplicate():
    assert duplicates([DOLO, ATORVA]) == [] and duplicates([]) == []


def test_duplicate_without_parseable_strength_has_no_sum():
    a = duplicates([DOLO, {"label": "P", "salts": [{"salt": "acetaminophen", "strength": ""}], "freq": ""}])[0]
    assert "per combined dose" not in a["detail"]


# SAFE-1 allergy
def test_penicillin_class_allergy():
    al = allergy([AUG], ["Penicillin"])
    assert [(a["severity"], a["type"], a["meds"]) for a in al] == [("HIGH", "ALLERGY", [0])]


def test_direct_salt_allergy():
    al = allergy([AUG], ["amoxicillin"])
    assert al[0]["severity"] == "HIGH" and al[0]["type"] == "ALLERGY"


def test_penicillin_cephalosporin_cross_reactivity():
    al = allergy([CEF], ["penicillin"])
    assert len(al) == 1 and al[0]["severity"] == "REVIEW" and al[0]["type"] == "CROSS_REACTIVITY"
    assert "1–2% cross-reactivity; confirm with doctor" in al[0]["detail"]


def test_cephalosporin_allergy_is_high():
    al = allergy([CEF], ["cephalosporins"])
    assert al[0]["severity"] == "HIGH" and al[0]["type"] == "ALLERGY"


def test_sulfa_hctz_caution():
    al = allergy([TELMA_H], ["sulfa drugs"])
    assert len(al) == 1 and al[0]["severity"] == "REVIEW" and al[0]["type"] == "ALLERGY"
    assert "hydrochlorothiazide" in al[0]["title"]


def test_nsaid_allergy():
    al = allergy([COMBI, DOLO], ["NSAIDs"])
    assert [a["meds"] for a in al] == [[0]] and al[0]["severity"] == "HIGH"


def test_no_allergy():
    assert allergy([DOLO, ATORVA], ["penicillin"]) == [] and allergy([AUG], []) == []


# SAFE-2 strip check
def test_strip_match():
    r = strip_check({"label": "s", "salts": [{"salt": "Paracetamol", "strength": "650 mg"}]}, [COMBI, DOLO])
    assert r["status"] == "MATCH" and r["med_index"] == 1


def test_strip_mismatch_detail():
    r = strip_check({"label": "s", "salts": [{"salt": "paracetamol", "strength": "500mg"}]}, [DOLO])
    assert r["status"] == "MISMATCH" and r["med_index"] == 0
    assert "Prescribed Dolo 650 Tablet (paracetamol 650mg) but strip is paracetamol 500mg" in r["detail"]


def test_strip_not_prescribed():
    r = strip_check({"label": "s", "salts": [{"salt": "cetirizine", "strength": "10mg"}]}, [DOLO, COMBI])
    assert r["status"] == "NOT_PRESCRIBED" and r["med_index"] is None


# SAFE-3 Jan Aushadhi
def test_jan_aushadhi_lookup():
    g = jan_aushadhi(AUG)
    assert g["price"] == 65 and g["indicative"] is True and "janaushadhi.gov.in" in g["source"]
    assert {"generic_name", "price", "pack", "indicative", "source"} <= set(g)
    assert jan_aushadhi(COMBI)["price"] == 18
    assert jan_aushadhi(CEF) is None
    assert jan_aushadhi({"label": "D", "salts": [{"salt": "paracetamol", "strength": "500mg"}]}) is None
    assert jan_aushadhi({"label": "D", "salts": [{"salt": "paracetamol", "strength": ""}]})["price"] == 14


def test_monthly_savings():
    # Dolo: 34.27/15 - 14/10 = 0.8847 x 3/day x 30 = 79.62 ; Augmentin: 22.342 - 6.5 = 15.842 x 2 x 30 = 950.52
    assert abs(monthly_savings([DOLO, AUG, CEF], [None, None, 260.0]) - 1030.14) < 0.05


def test_monthly_savings_missing_price_uses_brand_prices():
    med = {"label": "Combiflam Tablet", "salts": COMBI["salts"], "freq": "BD"}
    # no pack -> brand_prices taken as per-unit: (3 - 1.8) x 2 x 30 = 72
    assert abs(monthly_savings([med], [3.0]) - 72.0) < 1e-6
    assert monthly_savings([med], [None]) == 0.0 and monthly_savings([med], []) == 0.0


# SAFE-4 schedule
def test_schedule():
    assert schedule("OD") == ["Morning"]
    assert schedule("bd") == ["Morning", "Night"]
    assert schedule("1 tab TDS after food") == ["Morning", "Afternoon", "Night"]
    assert schedule("TID") == ["Morning", "Afternoon", "Night"]
    assert len(schedule("QID")) == 4
    assert schedule("hs") == ["Bedtime"]
    assert schedule("SOS for fever") == ["As needed"]
    assert schedule("1-0-1") == ["Morning", "Night"]
    assert schedule("take with food") == [] and schedule("") == [] and schedule(None) == []


# TEST-1 test lab
def test_testlab_all_pass():
    from core.testlab import run_cases
    res = run_cases()
    assert len(res) == 4 and all(set(r) == {"case", "expected", "got", "passed"} for r in res)
    assert all(r["passed"] for r in res), res

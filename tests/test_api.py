"""API tests. Run from the repo root: python -m pytest tests -q"""
import pytest


@pytest.fixture
def client(api_client):
    return api_client


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["dataset_rows"] == 630


def test_performance_matches_notebook(client):
    p = client.get("/api/model/performance").json()
    assert p["test_real_surveys"]["n"] == 60
    assert abs(p["test_real_surveys"]["mae"] - 5.387) < 0.01
    assert abs(p["test_real_surveys"]["r2"] - 0.617) < 0.01
    assert p["test_real_surveys"]["mae"] < p["persistence_real_surveys"]["mae"]


def test_forecasts_cover_all_districts(client):
    rows = client.get("/api/forecasts").json()["rows"]
    assert len(rows) == 30
    assert all(r["predicted_2025"] is not None and r["predicted_2026"] is not None for r in rows)


def test_explanation_adds_up(client):
    e = client.get("/api/model/explain", params={"district": "Rutsiro", "year": 2026}).json()
    total = e["base_value"] + sum(c["contribution"] for c in e["contributions"])
    assert abs(total - e["prediction"]) < 0.01


def test_predict_defaults_match_forecast(client):
    defaults = client.get("/api/predict/defaults", params={"district": "Huye", "year": 2025}).json()
    r = client.post("/api/predict", json={"district": "Huye", "year": 2025, "inputs": defaults["inputs"]})
    assert r.status_code == 200
    forecast = client.get("/api/forecasts", params={"district": "Huye"}).json()["rows"][0]
    assert abs(r.json()["prediction"] - forecast["predicted_2025"]) < 0.01


def test_predict_imputes_empty_inputs(client):
    r = client.post("/api/predict", json={"district": "Huye", "year": 2025, "inputs": {"rain_12m_mm": None}})
    assert r.status_code == 200
    assert "Rainfall, 12 months" in r.json()["missing_inputs_imputed"]


def test_bad_requests(client):
    assert client.get("/api/model/explain", params={"district": "Nowhere", "year": 2025}).status_code == 404
    assert client.get("/api/model/explain", params={"district": "Huye", "year": 2030}).status_code == 422
    bad = [
        {"district": "Huye", "year": 2025, "inputs": {"not_a_feature": 1}},
        {"district": "Huye", "year": 2025, "inputs": {"rain_12m_mm": -5}},
        {"district": "Huye", "year": 2030, "inputs": {}},
    ]
    for body in bad:
        assert client.post("/api/predict", json=body).status_code == 422


def test_viz_trends_province_production(client):
    r = client.get("/api/visualizations/trends", params={"variable": "sas_maize_production_t"}).json()
    assert len(r["series"]) == 5
    # Province totals add up to the national total
    total_2024 = sum(p["value"] for s in r["series"] for p in s["points"] if p["year"] == 2024)
    national_2024 = next(p["value"] for p in r["national"] if p["year"] == 2024)
    assert abs(total_2024 - national_2024) < 1
    # 2026 harvest data is partial, so the ranking stops at 2025
    assert r["partial_years"] == [2026] and r["comparison"]["to_year"] == 2025


def test_viz_trends_district_level_and_errors(client):
    r = client.get("/api/visualizations/trends", params={
        "variable": "temp_12m_c", "level": "district", "province": "Kigali City", "start_year": 2006}).json()
    assert [s["name"] for s in r["series"]] == ["Gasabo", "Kicukiro", "Nyarugenge"]
    assert r["comparison"]["change_kind"] == "diff"
    bad = [{"variable": "nope"}, {"variable": "rain_12m_mm", "start_year": 2025, "end_year": 2021},
           {"variable": "rain_12m_mm", "level": "country"}]
    for q in bad:
        assert client.get("/api/visualizations/trends", params=q).status_code == 422
    assert client.get("/api/visualizations/trends", params={"variable": "rain_12m_mm", "district": "Nowhere"}).status_code == 404


def test_viz_profile(client):
    p = client.get("/api/visualizations/profile", params={"district": "Huye"}).json()
    assert p["area"] == "Huye" and len(p["rows"]) == 6 and len(p["crops"]) == 5

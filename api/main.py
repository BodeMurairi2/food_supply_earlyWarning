"""HarvestWatch API.

Run from the repository root:
    uvicorn api.main:app --reload --port 8000
"""

import uvicorn
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api import config
from api.agents.analyst import AIUnavailable, AIUpstreamError, run_analysis, tavily_search
from api.schemas import AnalyzeRequest, HealthResponse, PredictRequest, PredictResponse, SearchRequest
from api.services.store import Store

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = Store()
    # Precompute predictions and SHAP values once, so requests stay fast.
    _ = store.historical, store.forecasts
    state["store"] = store
    yield
    state.clear()


def store() -> Store:
    return state["store"]


def guarded(fn, *args, **kwargs):
    """Translate service errors into HTTP responses."""
    try:
        return fn(*args, **kwargs)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e).strip("'\""))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


router = APIRouter(prefix="/api")
YEAR_RANGE = dict(ge=2006, le=2026)


@router.get("/health", response_model=HealthResponse)
def health():
    s = store()
    return {"status": "ok", "dataset_rows": int(s.df.shape[0]),
            "models_loaded": [config.EVAL_MODEL_PATH.name, config.FINAL_MODEL_PATH.name]}


@router.get("/metadata")
def metadata():
    return store().metadata()


@router.get("/locations")
def locations():
    return store().locations()


@router.get("/boundaries")
def boundaries():
    return store().boundaries


@router.get("/overview")
def overview(province: Optional[str] = None, district: Optional[str] = None,
             year: int = Query(2025, **YEAR_RANGE)):
    return guarded(store().overview, province, district, year)


@router.get("/historical")
def historical(province: Optional[str] = None, district: Optional[str] = None,
               year: Optional[int] = Query(None, ge=config.TEST_YEARS[0], le=config.TEST_YEARS[1])):
    return guarded(store().historical_table, province, district, year)


@router.get("/model/performance")
def performance():
    return store().performance()


@router.get("/model/feature-importance")
def feature_importance(model: str = Query("final", pattern="^(final|evaluation)$")):
    return store().feature_importance("final" if model == "final" else "evaluation")


@router.get("/model/explain")
def explain(district: str, year: int = Query(..., ge=config.TEST_YEARS[0], le=config.FORECAST_YEARS[1])):
    return guarded(store().explain, district, year)


@router.get("/forecasts")
def forecasts(province: Optional[str] = None, district: Optional[str] = None):
    return guarded(store().forecast_table, province, district)


@router.get("/district-series")
def district_series(district: str):
    return guarded(store().district_series, district)


@router.get("/predict/defaults")
def predict_defaults(district: str, year: int = Query(..., **YEAR_RANGE)):
    return guarded(store().inputs_for, district, year)


@router.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    return guarded(store().predict, req.district, req.year, req.inputs)


@router.get("/visualizations/variables")
def viz_variables():
    return store().viz_variables()


@router.get("/visualizations/trends")
def viz_trends(variable: str, level: str = Query("province", pattern="^(province|district)$"),
               province: Optional[str] = None, district: Optional[str] = None,
               start_year: int = Query(2021, **YEAR_RANGE), end_year: int = Query(2026, **YEAR_RANGE)):
    return guarded(store().viz_trends, variable, level, province, district, start_year, end_year)


@router.get("/visualizations/profile")
def viz_profile(province: Optional[str] = None, district: Optional[str] = None,
                start_year: int = Query(2021, **YEAR_RANGE), end_year: int = Query(2026, **YEAR_RANGE)):
    return guarded(store().viz_profile, province, district, start_year, end_year)


# ---------- AI Analyst ----------
# Analyses cost money and time, so identical requests are served from memory.
_ai_cache: dict = {}


async def ai_guarded(coro):
    try:
        return await coro
    except AIUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except AIUpstreamError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/ai/status")
def ai_status():
    return config.ai_status()


@router.get("/ai/context")
def ai_context(district: str, year: int = Query(..., ge=config.TEST_YEARS[0], le=config.FORECAST_YEARS[1])):
    return guarded(store().ai_context, district, year)


@router.post("/ai/search")
async def ai_search(req: SearchRequest):
    results = await ai_guarded(tavily_search(req.query, req.max_results))
    return {"query": req.query, "results": results}


@router.post("/ai/analyze")
async def ai_analyze(req: AnalyzeRequest):
    question = (req.question or "").strip() or None
    key = (req.district, req.year, question)
    if key in _ai_cache:
        return {**_ai_cache[key], "cached": True}
    context = guarded(store().ai_context, req.district, req.year)
    result = await ai_guarded(run_analysis(context, question))
    out = {"district": req.district, "year": req.year, "question": question, "context": context, **result}
    _ai_cache[key] = out
    return {**out, "cached": False}


app = FastAPI(title="HarvestWatch API", version="0.1.0",
              description="District food insecurity forecasts for Rwanda (random forest, NISR CFSVA target).",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["GET", "POST"], allow_headers=["*"])
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        port=8000,
        reload=True
    )

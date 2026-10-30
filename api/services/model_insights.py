"""How the model performs and what drives it: scores, importance and SHAP explanations."""

import pandas as pd

from api import config
from api.data.serialization import clean
from api.model.explainer import contribution_items
from api.model.metrics import classification_scores, risk_class, scores


def performance(ctx):
    rows, _ = ctx.models.historical
    survey = rows[rows["is_real_survey"]]
    train = ctx.dataset.df[ctx.dataset.df["year"] < config.TEST_YEARS[0]]
    by_year = [{"year": int(y), "observation_type": g["observation_type"].iloc[0], **scores(g["observed"], g["predicted"])}
               for y, g in rows.groupby("year")]
    by_province = [{"province": p, **scores(g["observed"], g["predicted"])} for p, g in survey.groupby("province")]
    class_agreement = (survey["observed_risk"] == survey["predicted_risk"]).mean()
    return {
        "evaluation_setup": "Model trained on 2006-2020, tested on 2021-2024. 2021 and 2024 are real CFSVA surveys; "
                            "2022-2023 are interpolated between them.",
        "train": scores(train[ctx.models.target], ctx.models.eval_model.predict(train[ctx.models.features])),
        "test_all_rows": scores(rows["observed"], rows["predicted"]),
        "test_real_surveys": scores(survey["observed"], survey["predicted"]),
        "persistence_real_surveys": scores(survey["observed"], survey["persistence"]),
        "risk_class_agreement_real_surveys": clean(class_agreement),
        "classification_real_surveys": classification_scores(
            survey["observed_risk"], survey["predicted_risk"], ctx.models.historical_class_probabilities.loc[survey.index]),
        "by_year": by_year,
        "by_province_real_surveys": by_province,
        "caveats": [
            "Training years 2019-2020 are interpolated using the 2021 survey, so the 2021 score is slightly optimistic.",
            "The test set contains 60 real survey values (30 districts x 2 rounds).",
        ],
    }


def feature_importance(ctx, model="final"):
    pipeline, explainer = (ctx.models.final_model, ctx.models.final_explainer) if model == "final" else (ctx.models.eval_model, ctx.models.eval_explainer)
    rf = pipeline.named_steps["regressor"]
    impurity = pd.Series(rf.feature_importances_, index=explainer.original_names).groupby(level=0).sum()
    _, shap_values = ctx.models.forecasts if model == "final" else ctx.models.historical
    mean_abs = shap_values.abs().mean()
    items = []
    for f in impurity.index:
        label, group, unit = config.FEATURE_INFO.get(f, (f, "Other", ""))
        items.append({"feature": f, "label": label, "group": group,
                      "impurity_importance": round(float(impurity[f]), 4),
                      "mean_abs_shap": round(float(mean_abs.get(f, 0.0)), 3)})
    items.sort(key=lambda d: d["mean_abs_shap"], reverse=True)
    return {
        "model": "final (2006-2024)" if model == "final" else "evaluation (2006-2020)",
        "shap_rows": "2025-2026 forecast rows" if model == "final" else "2021-2024 test rows",
        "note": "Importance shows how much a feature moves the model's predictions, not a causal effect.",
        "features": items,
    }


def explain(ctx, district, year):
    ctx.dataset.validate_location(district=district)
    if config.TEST_YEARS[0] <= year <= config.TEST_YEARS[1]:
        rows, shap_values = ctx.models.historical
        model_name = "evaluation (2006-2020)"
        base = ctx.models.eval_explainer.base_value
    elif config.FORECAST_YEARS[0] <= year <= config.FORECAST_YEARS[1]:
        rows, shap_values = ctx.models.forecasts
        model_name = "final (2006-2024)"
        base = ctx.models.final_explainer.base_value
    else:
        raise KeyError("Explanations are available for 2021-2026")
    mask = (rows["district"] == district) & (rows["year"] == year)
    row = rows[mask].iloc[0]
    contribution = shap_values[mask].iloc[0]
    return {
        "district": district, "province": row["province"], "year": year, "model": model_name,
        "prediction": clean(row["predicted"]), "risk": risk_class(row["predicted"]),
        "observed": clean(row.get("observed")) if "observed" in rows else None,
        "base_value": round(base, 3),
        "contributions": contribution_items(contribution, row),
        "note": "Contributions (SHAP) show how each input moved this prediction away from the average prediction. "
                "They describe the model, not causes.",
    }

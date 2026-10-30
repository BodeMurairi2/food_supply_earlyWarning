"""Health, metadata and locations."""

from api import config
from api.services import metadata as metadata_service


def health(ctx):
    return {"status": "ok", "dataset_rows": int(ctx.dataset.df.shape[0]),
            "models_loaded": [config.EVAL_MODEL_PATH.name, config.FINAL_MODEL_PATH.name]}


def metadata(ctx):
    return metadata_service.metadata(ctx)


def locations(ctx):
    return metadata_service.locations(ctx)


def boundaries(ctx):
    return ctx.dataset.boundaries

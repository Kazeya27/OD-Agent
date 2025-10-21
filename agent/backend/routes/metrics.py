#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prediction and metrics endpoints
"""

import math
from fastapi import APIRouter

router = APIRouter()


# @router.post("/predict")
# def predict_endpoint(payload: dict):
#     """
#     Predict future OD flows

#     Input:
#         {
#             "history": {"T": T1, "N": N, "ids": [...], "tensor": [[[...]]]},
#             "horizon": 12,
#             "method": "naive" | "moving_average",
#             "window": 3
#         }

#     Output:
#         {"T": T2, "N": N, "ids": [...], "tensor": [[[...]]]}
#     """
#     hist = payload.get("history", {})
#     horizon = int(payload.get("horizon", 0))
#     method = payload.get("method", "naive")
#     window = int(payload.get("window", 3))

#     T1 = int(hist.get("T", 0))
#     N = int(hist.get("N", 0))
#     ids = hist.get("ids", [])
#     tensor = hist.get("tensor", [])

#     if T1 == 0 or horizon <= 0 or not tensor:
#         return {"T": 0, "N": N, "ids": ids, "tensor": []}

#     if method == "naive":
#         last = tensor[-1]
#         pred = [last for _ in range(horizon)]
#     elif method == "moving_average":
#         w = max(1, min(window, T1))
#         acc = [[0.0 for _ in range(N)] for _ in range(N)]
#         for t in tensor[-w:]:
#             for i in range(N):
#                 for j in range(N):
#                     v = t[i][j]
#                     acc[i][j] += 0.0 if v is None else float(v)
#         avg = [[acc[i][j]/w for j in range(N)] for i in range(N)]
#         pred = [avg for _ in range(horizon)]
#     else:
#         pred = [[[0.0 for _ in range(N)] for _ in range(N)] for _ in range(horizon)]

#     return {"T": horizon, "N": N, "ids": ids, "tensor": pred}


@router.post("/growth")
def growth_endpoint(payload: dict):
    """
    Calculate growth rate

    Input:
        {"a": float, "b": float, "safe": true}

    Output:
        {"growth": float|null}
    """
    a = float(payload["a"])
    b = float(payload["b"])
    safe = bool(payload.get("safe", True))

    if a == 0.0:
        return {
            "growth": None if safe else math.copysign(math.inf, 1.0 if b >= 0 else -1.0)
        }

    return {"growth": (b - a) / abs(a)}


@router.post("/metrics")
def metrics_endpoint(payload: dict):
    """
    Calculate RMSE, MAE, MAPE

    Input:
        {"y_true": [[[...]]], "y_pred": [[[...]]]}

    Output:
        {"rmse": float, "mae": float, "mape": float|null}
    """

    def _flatten(v):
        if isinstance(v, (list, tuple)):
            for x in v:
                yield from _flatten(x)
        else:
            yield v

    y_true = list(_flatten(payload["y_true"]))
    y_pred = list(_flatten(payload["y_pred"]))

    if len(y_true) != len(y_pred):
        return {"error": "length mismatch between y_true and y_pred"}

    se = ae = ape_sum = 0.0
    n = n_mape = 0

    for yt, yp in zip(y_true, y_pred):
        if yt is None or yp is None:
            continue
        yt = float(yt)
        yp = float(yp)
        if math.isnan(yt) or math.isnan(yp):
            continue

        se += (yp - yt) ** 2
        ae += abs(yp - yt)
        n += 1

        if yt != 0.0:
            ape_sum += abs((yp - yt) / yt)
            n_mape += 1

    if n == 0:
        return {"error": "no valid numeric pairs"}

    rmse = math.sqrt(se / n)
    mae = ae / n
    mape = (ape_sum / n_mape) if n_mape > 0 else None

    return {"rmse": rmse, "mae": mae, "mape": mape}

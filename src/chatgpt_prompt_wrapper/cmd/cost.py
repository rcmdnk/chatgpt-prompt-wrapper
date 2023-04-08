import json
import logging
from pathlib import Path


def cost(cost: Path, log: logging.Logger) -> None:
    if not cost.exists():
        log.info("No cost data.")
        return
    with open(cost, "r") as f:
        cost_data = json.load(f)
    log.info("Month, EstimatedCost(USD)")
    for k, v in cost_data.items():
        log.info(f"{k}, {v:.6f}")

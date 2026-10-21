import math
import re


def training_metric(line: str):
    match = re.search(r'(\d+)\s*/\s*(\d+).*?(?:avr_loss|loss)=([0-9.eE+-]+)', line)
    if not match:
        return None
    try:
        step, total, loss = int(match[1]), int(match[2]), float(match[3])
    except ValueError:
        return None
    if step < 1 or total < step or not math.isfinite(loss):
        return None
    return step, total, loss

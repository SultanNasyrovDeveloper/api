def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(v, hi))


def safe_div(a: float, b: float) -> float:
    return 0.0 if b == 0 else a / b


def geometric_mean(weights_and_values: list[tuple[float, float]]) -> float:
    """
    weights_and_values = [(weight, value_normalized_0_1), ...]
    """
    total_weight = sum(w for w, _ in weights_and_values)
    if total_weight == 0:
        return 0.0

    product = 1.0
    for w, v in weights_and_values:
        v = clamp(v)
        if v <= 0:
            return 0.0
        product *= v**w

    return product ** (1 / total_weight)

#!/usr/bin/env python3
"""赔率去水 + 与模型概率的混合展示。
回测结论:足球收盘盘口比模型更准,融合成单值反而更差 —— 因此对外不融合,而是并列展示
模型概率 / 盘口隐含概率 / 分歧,由前端呈现。此模块提供去水与分歧计算。"""


def devig_proportional(odds):
    """欧赔列表(如 [1X2] 的 [oh,od,oa])-> 隐含概率(比例去水)。无效返回 None。"""
    if not odds or any((o is None or o <= 1) for o in odds):
        return None
    inv = [1.0 / o for o in odds]
    s = sum(inv)
    return [x / s for x in inv]


def devig_shin(odds, iters=100):
    """Shin 方法去水(校正热门-冷门偏差),两向或多向通用。"""
    p = devig_proportional(odds)
    if p is None:
        return None
    inv = [1.0 / o for o in odds]
    booksum = sum(inv)
    z = 0.0
    for _ in range(iters):
        denom = sum(((z * z + 4 * (1 - z) * (q * q) / booksum) ** 0.5) for q in inv) or 1e-9
        z_new = (denom - 2) / (len(inv) - 2) if len(inv) > 2 else 0.0
        z_new = max(0.0, min(z_new, 0.2))
        if abs(z_new - z) < 1e-9:
            z = z_new; break
        z = z_new
    out = []
    for q in inv:
        pi = (((z * z + 4 * (1 - z) * (q * q) / booksum) ** 0.5) - z) / (2 * (1 - z)) if z < 1 else q / booksum
        out.append(pi)
    s = sum(out) or 1e-9
    return [x / s for x in out]


def divergence(model, market, labels):
    """返回模型相对盘口最偏离的一档,供前端展示"分歧洞察"。"""
    if not market:
        return None
    diffs = [(labels[i], model[i] - market[i]) for i in range(len(model))]
    lab, d = max(diffs, key=lambda x: abs(x[1]))
    return {"outcome": lab, "delta_pt": round(d * 100, 1)}

"""Score one round from JSON on stdin. Null means excluded, never zero."""
import json
import sys
from statistics import mean

WEIGHTS = (25, 15, 20, 25, 15)
GROUPS = ((0.60, range(3)), (0.40, range(3, 5)))


def composite(scores):
    groups = []
    for share, indices in GROUPS:
        observed = [i for i in indices if scores[i] is not None]
        if observed:
            total = sum(scores[i] * WEIGHTS[i] for i in observed)
            groups.append((share, total / sum(WEIGHTS[i] for i in observed)))
    if groups:
        return sum(share * value for share, value in groups) / sum(share for share, _ in groups)
    return None


def score_round(items):
    question_scores = {}
    columns = [[] for _ in WEIGHTS]
    for item in items:
        key, scores = item["id"], item["scores"]
        if not isinstance(key, str) or not key.strip() or key in question_scores:
            raise ValueError("需要唯一非空题号")
        if not isinstance(scores, list) or len(scores) != len(WEIGHTS):
            raise ValueError("每题必须有五项分数")
        for values, score in zip(columns, scores):
            if score is not None:
                if type(score) is not int or not 0 <= score <= 5:
                    raise ValueError("单项分数必须是 0–5 整数或 null")
                values.append(score)
        value = composite(scores)
        question_scores[key] = round(value, 2) if value is not None else None
    dimensions = [mean(column) if column else None for column in columns]
    total = composite(dimensions)
    return {"questions_5": question_scores, "observations": [len(c) for c in columns],
            "dimensions_5": [round(d, 2) if d is not None else None for d in dimensions],
            "round_100": round(total * 20, 1) if total is not None else None}


if __name__ == "__main__":
    try:
        print(json.dumps(score_round(json.load(sys.stdin)), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, TypeError) as err:
        sys.exit(f"评分输入错误：{err}")

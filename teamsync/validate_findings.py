from .schema import Review


def validate(review: Review, diff: dict) -> tuple[Review, int]:
    valid = [f for f in review.findings if f.line in diff["positions"].get(f.file, [])]
    return review.model_copy(update={"findings": valid}), len(review.findings) - len(valid)

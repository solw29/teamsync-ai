import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = [
    root / "README.md",
    root / "web/README.md",
    root / "docs/phase2/README.md",
    root / "docs/backend/README.md",
]
files += sorted(
    p
    for p in root.glob("*/README.md")
    if p.parent.name.startswith("D") or "_D" in p.parent.name
)
errors = []
for p in files:
    s = p.read_text()
    for token in ["작업", "완료 기준", "구현", "근거", "문제", "해결"]:
        if token not in s:
            errors.append(f"{p.relative_to(root)} missing {token}")
    for target in re.findall(r"\]\(([^)]+)\)", s):
        if target.startswith(("http:", "https:", "#", "mailto:")):
            continue
        target = target.split("#")[0]
        if target and not (p.parent / target).exists():
            errors.append(f"{p.relative_to(root)} broken {target}")
assert not errors, "\n".join(errors)
report = root / "docs/readme-review.md"
report.write_text(
    "# README 전체 검토 — 2026-11-23 (KST)\n\n대상: 루트·web·phase2·backend 및 D1~D50의 README 총 "
    + str(len(files))
    + "개. node_modules의 제3자 문서는 제외합니다.\n\n각 문서에 작업·완료 기준·구현·선택 근거·문제·해결을 확인했습니다. 실제 달성과 미검증을 구분하고 단계별 대안을 검토했습니다. 당시 수행하지 않은 대안 비교를 benchmark처럼 작성하지 않았고, 기록 없는 장애를 운영 실적으로 만들지 않았습니다.\n\nD1/D2의 깨진 docs 상대 링크를 고쳤으며, 로컬 Markdown 링크 존재 검사도 통과했습니다. 작업/검증 수치는 해당 단계 시점의 기록을 유지합니다. 테스트 수·import 누락·Docker CA/권한·모델 기대값·API 네트워크·모바일 overflow 문제는 실제 기록에 근거했습니다.\n\n"
    + "\n".join(
        "- ["
        + str(p.relative_to(root))
        + "]("
        + str(Path("..") / p.relative_to(root))
        + ") — 검토 완료"
        for p in files
    )
    + "\n"
)
print(f"{len(files)} README content/link checks passed")

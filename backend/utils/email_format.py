import re
import json


META_BLOCK_RE = re.compile(
    r"^\s*---HACKMATCH-META---\s*\r?\n(?P<meta>.*?)\r?\n---END-META---\s*(?:\r?\n\r?\n)?(?P<body>.*)$",
    flags=re.DOTALL,
)


def format_agent_email(meta: dict, body: str) -> tuple[str, str]:
    purpose = str(meta["purpose"])
    subject = f"[HACKMATCH] {purpose.replace('_', ' ').title()}: {str(meta['match_id'])[:6]}"

    meta_lines = ["---HACKMATCH-META---"]
    for key, value in meta.items():
        meta_lines.append(f"{key}: {value}")
    meta_lines.append("---END-META---")

    full_body = "\n".join(meta_lines) + f"\n\n{body.strip()}"
    return subject, full_body


def parse_agent_email(raw_body: str) -> dict:
    if not raw_body:
        return {"meta": {}, "body": raw_body}

    match = META_BLOCK_RE.match(raw_body)
    if not match:
        return {"meta": {}, "body": raw_body}

    meta: dict[str, object] = {}
    for line in match.group("meta").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if key == "synergy_score":
            try:
                meta[key] = float(value)
            except ValueError:
                meta[key] = value
            continue

        if key == "questions":
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    meta[key] = parsed
                else:
                    meta[key] = value
            except Exception:
                meta[key] = value
            continue

        meta[key] = value

    return {
        "meta": meta,
        "body": match.group("body").strip(),
    }

_TRIVIAL = {"lgtm", "thanks", "thank you", "done", "+1", "ok", "okay", "nice", "great"}


def extract_reactions(item):
    r = (item or {}).get("reactions") or {}
    return {"plus": r.get("+1", 0), "total": r.get("total_count", 0)}


def is_authority(login, allowed):
    return login is not None and login.lower() in allowed


def is_substantive(body, min_len=40):
    if not body:
        return False
    text = body.strip()
    if len(text) < min_len:
        return False
    if text.lower().strip(".!") in _TRIVIAL:
        return False
    return True


def shape_record(kind, repo, author, created_at, html_url, body, context,
                 reactions=None, adopted=None):
    return {
        "repo": repo,
        "kind": kind,
        "author": author,
        "created_at": created_at,
        "html_url": html_url,
        "context": context,
        "body": (body or "").strip(),
        "reactions": reactions or {"plus": 0, "total": 0},
        "adopted": adopted,
    }

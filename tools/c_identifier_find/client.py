from __future__ import annotations

import json
import urllib.request
import urllib.parse
import urllib.error


def _request(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"ok": False, "error": f"HTTP {e.code}: {body}"}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"连接失败: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def call_find(server_url: str, name: str, fuzzy: bool = False) -> dict:
    params = urllib.parse.urlencode({"name": name, "fuzzy": "1" if fuzzy else "0"})
    return _request(f"{server_url}/find?{params}")


def call_status(server_url: str) -> dict:
    return _request(f"{server_url}/status")

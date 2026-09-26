#!/usr/bin/env python3
"""Fetch new messages from Mira's IMAP inbox into the local Mira queue."""

from __future__ import annotations

import argparse
import hashlib
import imaplib
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from pathlib import Path


def account_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    section = ""
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line in {"IMAP:", "SMTP:"}:
            section = line[:-1]
        elif section == "IMAP" and ":" in line:
            key, value = line.split(":", 1)
            values[key.strip().upper()] = value.strip()
    required = {"HOST", "PORT", "USER", "PASS"}
    missing = required - values.keys()
    if missing:
        raise ValueError(f"missing IMAP fields: {', '.join(sorted(missing))}")
    return values


def load_state(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return set(value if isinstance(value, list) else [])
    except (OSError, json.JSONDecodeError):
        return set()


def save_state(path: Path, state: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(sorted(state), stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def message_key(raw: bytes) -> str:
    message = BytesParser(policy=policy.default).parsebytes(raw, headersonly=True)
    message_id = str(message.get("Message-ID", "")).strip()
    return message_id or hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", type=Path, default=Path("/home/mira/data/mail-account.nf0"))
    parser.add_argument("--queue", type=Path, default=Path("/home/mira/inbound/queue"))
    parser.add_argument("--state", type=Path, default=Path("/home/mira/inbound/.imap-mira-state.json"))
    args = parser.parse_args()
    os.umask(0o002)

    values = account_values(args.account)
    port = int(values["PORT"])
    security = values.get("SECS", "").lower()
    client = imaplib.IMAP4_SSL(values["HOST"], port) if port == 993 or security == "ssl" else imaplib.IMAP4(values["HOST"], port)
    state = load_state(args.state)
    imported = 0
    try:
        if security in {"starttls", "tls"} and port != 993:
            client.starttls()
        client.login(values["USER"], values["PASS"])
        client.select("INBOX", readonly=True)
        status, data = client.search(None, "ALL")
        if status != "OK":
            raise RuntimeError("IMAP search failed")
        for number in data[0].split():
            status, response = client.fetch(number, "(RFC822)")
            if status != "OK" or not response or not isinstance(response[0], tuple):
                continue
            raw = response[0][1]
            key = message_key(raw)
            if key in state:
                continue
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            target = args.queue / f"{stamp}-{secrets.token_hex(4)}.eml"
            args.queue.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=args.queue)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw)
                os.replace(temporary, target)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            state.add(key)
            imported += 1
        save_state(args.state, state)
    finally:
        try:
            client.logout()
        except Exception:
            pass
    print(f"imported={imported}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

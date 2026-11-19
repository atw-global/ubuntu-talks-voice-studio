"""Local classroom server for browser QA.

Serves the built static classroom and the real Lesson 1 access rules.
Audio is a generated tone, not the private R2 master.
"""
from __future__ import annotations

import json
import pathlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BACKEND = pathlib.Path(__file__).resolve().parents[3] / "backend"
STATIC = pathlib.Path(__file__).resolve().parents[2] / "static"
sys.path.insert(0, str(BACKEND))

from app.lesson1_learning import access_catalog, resolve_stage  # noqa: E402
from app.lesson_audio import clip_audio  # noqa: E402

PHRASES = [
    ("Thando", "Sawubona.", "Hello (one person)."),
    ("Themba", "Sanibonani.", "Hello (a group)."),
    ("Thando", "Unjani?", "How are you? (one person)"),
    ("Themba", "Ninjani?", "How are you? (a group)"),
    ("Thando", "Ngiyaphila.", "I am fine."),
    ("Themba", "Ngiyaphila, wena unjani?", "I'm fine. And how are you?"),
    ("Thando", "Sisaphila, nina ninjani?", "We are fine. How are you all?"),
    ("Themba", "Ngiyabonga.", "Thank you."),
    ("Thando", "Sawubona.", "Hello (one person)."),
    ("Themba", "Sanibonani.", "Hello (a group)."),
    ("Thando", "Unjani?", "How are you? (one person)"),
    ("Themba", "Ninjani?", "How are you? (a group)"),
    ("Thando", "Sala kahle.", "Stay well."),
    ("Themba", "Ngizokubona kusasa.", "See you tomorrow."),
]


def manifest(duration: float) -> dict:
    cues = []
    for index, (speaker, text, meaning) in enumerate(PHRASES):
        start = round(index * (duration / len(PHRASES)), 3)
        cues.append({
            "cue": index + 3,
            "speaker": speaker,
            "text": text,
            "meaning": meaning,
            "start": start,
            "end": round(start + 0.4, 3),
        })
    return {
        "version": "native-greeting-lesson01-v1",
        "duration_seconds": duration,
        "cue_count": len(cues),
        "instructor_english_audio": False,
        "commercial_release": False,
        "cues": cues,
    }


class Handler(BaseHTTPRequestHandler):
    audio = b""

    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, status: int, body: bytes, content_type: str, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/api/ubuntu/azure/lesson1/sample/synced-dialogue":
            self._send(200, json.dumps(manifest(8)).encode(), "application/json")
            return
        if path == "/api/ubuntu/azure/lesson1/sample/native-only.mp3":
            status, body, extra = clip_audio(self.audio, self.headers.get("Range"))
            self._send(status, body, "audio/mpeg", {"Accept-Ranges": "bytes", **extra})
            return
        if path == "/api/ubuntu/azure/lesson1/classroom/access":
            body = access_catalog()
            body["enrolled"] = False
            self._send(200, json.dumps(body).encode(), "application/json")
            return
        if path.startswith("/api/ubuntu/azure/lesson1/classroom/stages/"):
            stage_id = path.rsplit("/", 1)[-1]
            status, body = resolve_stage(stage_id, enrolled=False)
            self._send(status, json.dumps(body).encode(), "application/json")
            return
        target = (STATIC / path.lstrip("/")).resolve()
        if not str(target).startswith(str(STATIC)) or not target.is_file():
            self._send(404, b"not found", "text/plain")
            return
        kind = "text/html" if target.suffix == ".html" else "text/css" if target.suffix == ".css" else "application/javascript" if target.suffix == ".js" else "image/jpeg" if target.suffix == ".jpg" else "application/octet-stream"
        self._send(200, target.read_bytes(), kind)


def main() -> None:
    audio = pathlib.Path(sys.argv[1])
    Handler.audio = audio.read_bytes()
    server = ThreadingHTTPServer(("127.0.0.1", 4177), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()

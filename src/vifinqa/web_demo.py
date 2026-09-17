"""Zero-dependency portfolio web demo for the extended ViFinQA project."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any, Optional

from .diagnostics import project_health
from .semantic_parser import parse_question


HTML = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ViFinQA Auditable Agent</title><style>
:root{--bg:#07111f;--panel:#0d1b2d;--line:#203652;--cyan:#43e8d8;--blue:#69a7ff;--text:#edf6ff;--muted:#96abc2;--warn:#ffcc66}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 85% 0,#123154 0,transparent 32%),var(--bg);color:var(--text);font:15px Inter,Segoe UI,sans-serif;min-height:100vh}
.shell{max-width:1280px;margin:auto;padding:34px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:42px}.brand{font-weight:800;letter-spacing:.08em}.brand b{color:var(--cyan)}.pill{border:1px solid #2c4969;border-radius:99px;padding:8px 13px;color:var(--muted)}
.hero{display:grid;grid-template-columns:1.2fr .8fr;gap:28px;align-items:center}.eyebrow{color:var(--cyan);font-weight:700;letter-spacing:.15em;font-size:12px}h1{font-size:clamp(42px,6vw,78px);line-height:.96;margin:16px 0 22px;letter-spacing:-.055em}.lead{color:var(--muted);font-size:18px;line-height:1.7;max-width:760px}
.metrics,.pipeline{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.card{background:linear-gradient(145deg,#102239,#0b1727);border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 18px 50px #0004}.metric strong{display:block;color:var(--cyan);font-size:30px}.metric span{color:var(--muted)}
.workspace{margin-top:34px;padding:24px}.inputrow{display:flex;gap:12px}textarea{flex:1;resize:vertical;min-height:76px;background:#071421;border:1px solid #294663;color:var(--text);border-radius:13px;padding:15px;font:inherit;outline:none}textarea:focus{border-color:var(--cyan)}button{border:0;border-radius:13px;padding:0 23px;background:linear-gradient(135deg,var(--cyan),var(--blue));color:#04101d;font-weight:800;cursor:pointer}.samples{display:flex;gap:8px;flex-wrap:wrap;margin:15px 0}.sample{background:#122740;color:#bcd2e8;border:1px solid #294663;padding:8px 11px;font-size:12px}
.result{display:none;margin-top:18px;grid-template-columns:.9fr 1.1fr;gap:14px}.result.show{display:grid}.label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.1em}.value{font-size:18px;margin:7px 0 16px}.tags{display:flex;gap:7px;flex-wrap:wrap}.tag{padding:7px 10px;border-radius:9px;background:#16304b;color:#c8e7ff}.flow{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:13px}.step{border-left:3px solid var(--cyan);background:#0a1828;padding:12px;border-radius:8px;color:#bdd0e3}.note{color:var(--warn);font-size:13px;margin-top:14px}
@media(max-width:800px){.hero,.result{grid-template-columns:1fr}.flow{grid-template-columns:1fr 1fr}.shell{padding:20px}.inputrow{flex-direction:column}button{padding:15px}}
</style></head><body><main class="shell">
<header class="top"><div class="brand"><b>VIFINQA</b> / AUDITABLE AGENT</div><div class="pill" id="health">checking system…</div></header>
<section class="hero"><div><div class="eyebrow">EVIDENCE-FIRST FINANCIAL AI</div><h1>Answers you can<br>trace and replay.</h1><p class="lead">Phân tích câu hỏi tài chính tiếng Việt, truy hồi bảng nguồn, lập kế hoạch tính toán và sinh Pandas có thể kiểm chứng.</p></div><div class="metrics"><div class="card metric"><strong id="questions">1,012</strong><span>benchmark questions</span></div><div class="card metric"><strong>97.2%</strong><span>document F2</span></div><div class="card metric"><strong>5,941</strong><span>evidence bindings</span></div><div class="card metric"><strong>3</strong><span>auditor models</span></div></div></section>
<section class="card workspace"><div class="label">Question analyzer</div><div class="inputrow"><textarea id="q">Tỷ trọng lợi nhuận sau thuế trên doanh thu của FPT năm 2023 là bao nhiêu phần trăm?</textarea><button onclick="analyze()">Phân tích</button></div>
<div class="samples"><button class="sample" onclick="pick(this)">Lợi nhuận sau thuế của FPT năm 2023 là bao nhiêu tỷ đồng?</button><button class="sample" onclick="pick(this)">So sánh doanh thu FPT năm 2022 và 2023</button><button class="sample" onclick="pick(this)">Năm nào VCB có lợi nhuận cao nhất giai đoạn 2019–2023?</button></div>
<div class="result" id="result"><div class="card"><div class="label">Structured intent</div><div class="value" id="operation"></div><div class="label">Entities</div><div class="tags" id="entities"></div><br><div class="label">Periods & scope</div><div class="tags" id="periods"></div></div><div class="card"><div class="label">Detected metrics</div><div class="tags" id="metrics"></div><div class="flow"><div class="step">01 Parse</div><div class="step">02 Retrieve</div><div class="step">03 Ground</div><div class="step">04 Verify</div></div><div class="note" id="ambiguities"></div></div></div></section>
</main><script>
const tag=x=>`<span class="tag">${x}</span>`;function pick(b){document.querySelector('#q').value=b.textContent;analyze()}
async function analyze(){let q=document.querySelector('#q').value.trim();if(!q)return;let r=await fetch('/api/analyze',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({question:q})});let d=await r.json();document.querySelector('#result').classList.add('show');document.querySelector('#operation').textContent=d.operation;document.querySelector('#entities').innerHTML=d.entities.map(x=>tag(x.ticker||x.name)).join('')||tag('chưa xác định');document.querySelector('#periods').innerHTML=d.periods.map(x=>tag(x.year)).join('')+tag(d.scope)+tag(d.output_unit);document.querySelector('#metrics').innerHTML=d.requested_metrics.map(tag).join('')||tag('cần semantic planner');document.querySelector('#ambiguities').textContent=d.ambiguities.length?'Cần làm rõ: '+d.ambiguities.join(', '):'Câu hỏi đã đủ thông tin cơ bản.'}
fetch('/api/health').then(r=>r.json()).then(d=>{document.querySelector('#health').textContent=d.status==='ready'?'● full pipeline ready':'● source & demo ready';document.querySelector('#questions').textContent=d.execution_plan.questions.toLocaleString('en-US')});
</script></body></html>"""


def analyze_question(question: str) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")
    if len(question) > 2000:
        raise ValueError("question is too long")
    return asdict(parse_question(question.strip()))


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "ViFinQADemo/1.0"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: Any) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/":
            self._send(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/health":
            self._json(200, project_health())
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path != "/api/analyze":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 16_384:
                raise ValueError("request body is too large")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            self._json(200, analyze_question(payload.get("question", "")))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            self._json(400, {"error": str(error)})

    def log_message(self, message: str, *args: object) -> None:
        print(f"[web] {self.address_string()} {message % args}")


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    print(f"ViFinQA demo: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

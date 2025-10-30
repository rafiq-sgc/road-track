from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
import threading
from typing import Any, Dict, Optional, Union

from app.services.processor import VideoProcessor

app = FastAPI(title="Road Tracker")


class StartRequest(BaseModel):
    source: Union[int, str] = 0


class SignalRequest(BaseModel):
    state: str  # "red" or "green"


# Singleton processor for simplicity in dev
_processor_lock = threading.Lock()
_processor: Optional[VideoProcessor] = None


def get_processor() -> VideoProcessor:
    global _processor
    with _processor_lock:
        if _processor is None:
            _processor = VideoProcessor()
        return _processor


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return (
        """
        <!doctype html>
        <html>
        <head>
          <meta charset=\"utf-8\" />
          <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
          <title>Road Tracker</title>
          <style>
            :root{--bg:#0b1220;--panel:#111827;--text:#e5e7eb;--muted:#9ca3af;--accent:#2563eb;--danger:#ef4444;--warn:#f59e0b;--ok:#22c55e}
            *{box-sizing:border-box}
            body{font-family:system-ui,Arial;margin:0;background:var(--bg);color:var(--text)}
            header{padding:12px 16px;background:#0a0f1a;position:sticky;top:0;z-index:10;border-bottom:1px solid #1f2937}
            h3{margin:0;font-weight:600}
            main{padding:16px}
            .grid{display:grid;grid-template-columns:1.5fr 1fr;gap:16px}
            .panel{background:var(--panel);border:1px solid #1f2937;border-radius:10px;overflow:hidden}
            .panel > .head{padding:10px 12px;border-bottom:1px solid #1f2937;display:flex;justify-content:space-between;align-items:center}
            .panel > .body{padding:12px}
            img, video{max-width:100%;display:block}
            .controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
            input[type=text]{padding:8px 10px;width:360px;background:#0f172a;color:var(--text);border:1px solid #334155;border-radius:8px}
            button, select{padding:8px 12px;border-radius:8px;border:1px solid #334155;background:#111827;color:var(--text);cursor:pointer}
            button.primary{background:var(--accent);border-color:#1d4ed8}
            .badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px}
            .b-warn{background:rgba(245,158,11,.15);color:#fbbf24}
            .b-danger{background:rgba(239,68,68,.15);color:#f87171}
            .b-info{background:rgba(37,99,235,.15);color:#60a5fa}
            .b-ok{background:rgba(34,197,94,.15);color:#86efac}
            .alerts{max-height:70vh;overflow:auto;display:flex;flex-direction:column;gap:10px}
            .alert{padding:10px 12px;border:1px solid #1f2937;border-radius:10px;background:#0f172a}
            .alert .row{display:flex;gap:8px;align-items:center;justify-content:space-between}
            .filters{display:flex;gap:8px;flex-wrap:wrap}
            .muted{color:var(--muted)}
          </style>
        </head>
        <body>
          <header><h3>Road Tracker</h3></header>
          <main>
            <div class=\"panel\" style=\"margin-bottom:16px\"> 
              <div class=\"head\"><div>Controls</div></div>
              <div class=\"body\">
                <div class=\"controls\">
                  <input id=\"source\" type=\"text\" placeholder=\"0 (webcam) or /abs/path/video.mp4\" />
                  <button class=\"primary\" onclick=\"start()\">Start</button>
                  <button onclick=\"stopProc()\">Stop</button>
                  <label>Signal</label>
                  <select id=\"signal\"><option>green</option><option>red</option></select>
                  <button onclick=\"setSignal()\">Apply</button>
                  <label><input type=\"checkbox\" id=\"autoScroll\" checked /> Auto-scroll alerts</label>
                </div>
              </div>
            </div>
            <div class=\"grid\">
              <div class=\"panel\">
                <div class=\"head\"><div>Live stream</div></div>
                <div class=\"body\"><img id=\"stream\" src=\"/stream\" /></div>
              </div>
              <div class=\"panel\">
                <div class=\"head\">
                  <div>Alerts</div>
                  <div class=\"filters\">
                    <label><input type=\"checkbox\" class=\"flt\" value=\"red_light_violation\" checked /> Red Light</label>
                    <label><input type=\"checkbox\" class=\"flt\" value=\"lane_violation\" checked /> Lane</label>
                    <label><input type=\"checkbox\" class=\"flt\" value=\"speeding\" checked /> Speeding</label>
                    <label><input type=\"checkbox\" class=\"flt\" value=\"wrong_way\" checked /> Wrong-way</label>
                    <label><input type=\"checkbox\" class=\"flt\" value=\"no_helmet\" checked /> Helmet</label>
                    <label><input type=\"checkbox\" class=\"flt\" value=\"plate_read\" checked /> Plate</label>
                  </div>
                </div>
                <div class=\"body\">
                  <div id=\"alerts\" class=\"alerts\"></div>
                </div>
              </div>
            </div>
          </main>
          <script>
          const typeBadge = (t)=>{
            const map={
              red_light_violation:['b-danger','Red Light'],
              lane_violation:['b-warn','Lane'],
              speeding:['b-info','Speeding'],
              wrong_way:['b-danger','Wrong-way'],
              no_helmet:['b-danger','No Helmet'],
              plate_read:['b-ok','Plate']
            };
            const m=map[t]||['b-info',t];
            return `<span class="badge ${m[0]}">${m[1]}</span>`;
          }
          function fmt(ts){
            try{ const d=new Date(ts*1000);return d.toLocaleTimeString(); }catch(e){ return '' }
          }
          function selectedTypes(){
            return Array.from(document.querySelectorAll('.flt'))
              .filter(el=>el.checked).map(el=>el.value);
          }
          async function start(){
            const source = document.getElementById('source').value || 0;
            await fetch('/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:isNaN(Number(source))?source:Number(source)})});
            document.getElementById('stream').src='/stream?ts='+Date.now();
          }
          async function stopProc(){ await fetch('/stop',{method:'POST'}); }
          async function setSignal(){ const s=document.getElementById('signal').value; await fetch('/signal',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({state:s})}); }

          let lastRendered = 0;
          async function pollAlerts(){
            try{
              const r=await fetch('/alerts');
              const j=await r.json();
              const list=j.alerts||[];
              renderAlerts(list);
            }catch(e){}
            finally{ setTimeout(pollAlerts, 800); }
          }

          function renderAlerts(list){
            const types = new Set(selectedTypes());
            const wrap = document.getElementById('alerts');
            wrap.innerHTML = '';
            for(const a of list){
              if(!types.has(a.type)) continue;
              const t=fmt(a.ts);
              const content = JSON.stringify(a.info || {});
              const html = `
                <div class="alert">
                  <div class="row">
                    <div>${typeBadge(a.type)}</div>
                    <div class="muted">${t}</div>
                  </div>
                  <div class="muted">track: ${a.track_id ?? '-'} </div>
                  <div style="margin-top:4px">${content}</div>
                </div>`;
              wrap.insertAdjacentHTML('beforeend', html);
            }
            if(document.getElementById('autoScroll').checked){ wrap.scrollTop = wrap.scrollHeight; }
          }

          pollAlerts();
          </script>
        </body>
        </html>
        """
    )


@app.post("/start")
async def start(req: StartRequest) -> Dict[str, Any]:
    proc = get_processor()
    ok = proc.start(req.source)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to open source")
    return {"status": "started"}


@app.post("/stop")
async def stop() -> Dict[str, Any]:
    proc = get_processor()
    proc.stop()
    return {"status": "stopped"}


@app.post("/signal")
async def set_signal(req: SignalRequest) -> Dict[str, Any]:
    proc = get_processor()
    proc.set_signal_state(req.state)
    return {"state": proc.get_signal_state()}


@app.get("/alerts")
async def alerts() -> JSONResponse:
    proc = get_processor()
    return JSONResponse(proc.get_recent_alerts())


@app.get("/stream")
async def stream() -> StreamingResponse:
    proc = get_processor()
    return StreamingResponse(proc.mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

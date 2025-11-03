"""Enhanced FastAPI application with WebSocket, metrics, evidence, and calibration UI."""
import logging
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import threading
import json
import asyncio
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from app.services.processor_v2 import VideoProcessorV2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Road Tracker Pro", version="2.0.0")

# Serve violations folder
violations_path = Path("violations")
violations_path.mkdir(exist_ok=True)
app.mount("/violations", StaticFiles(directory=str(violations_path)), name="violations")


class StartRequest(BaseModel):
    source: Union[int, str] = 0


class SignalRequest(BaseModel):
    state: str  # "red" or "green"


# Singleton processor
_processor_lock = threading.Lock()
_processor: Optional[VideoProcessorV2] = None

# WebSocket clients
_ws_clients: List[WebSocket] = []
_ws_lock = threading.Lock()


def get_processor() -> VideoProcessorV2:
    global _processor
    with _processor_lock:
        if _processor is None:
            _processor = VideoProcessorV2()
            logger.info("Initialized VideoProcessorV2")
        return _processor


async def broadcast_alert(alert: Dict):
    """Broadcast alert to all connected WebSocket clients."""
    with _ws_lock:
        dead_clients = []
        for client in _ws_clients:
            try:
                await client.send_json(alert)
            except Exception:
                dead_clients.append(client)
        
        for client in dead_clients:
            _ws_clients.remove(client)


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Main UI with WebSocket support and enhanced features."""
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Road Tracker Pro</title>
  <style>
    :root{--bg:#0b1220;--panel:#111827;--text:#e5e7eb;--muted:#9ca3af;--accent:#2563eb;--danger:#ef4444;--warn:#f59e0b;--ok:#22c55e}
    *{box-sizing:border-box}
    body{font-family:system-ui,Arial;margin:0;background:var(--bg);color:var(--text)}
    header{padding:12px 16px;background:#0a0f1a;position:sticky;top:0;z-index:10;border-bottom:1px solid #1f2937;display:flex;justify-content:space-between;align-items:center}
    h3{margin:0;font-weight:600}
    .theme-toggle{padding:6px 12px;background:var(--panel);border:1px solid #334155;border-radius:6px;cursor:pointer;color:var(--text)}
    main{padding:16px}
    .grid{display:grid;grid-template-columns:1.5fr 1fr;gap:16px}
    .panel{background:var(--panel);border:1px solid #1f2937;border-radius:10px;overflow:hidden}
    .panel > .head{padding:10px 12px;border-bottom:1px solid #1f2937;display:flex;justify-content:space-between;align-items:center}
    .panel > .body{padding:12px}
    img{max-width:100%;display:block}
    .controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
    input[type=text]{padding:8px 10px;width:360px;background:#0f172a;color:var(--text);border:1px solid #334155;border-radius:8px}
    button, select{padding:8px 12px;border-radius:8px;border:1px solid #334155;background:#111827;color:var(--text);cursor:pointer}
    button.primary{background:var(--accent);border-color:#1d4ed8;font-weight:600}
    button:hover{opacity:0.9}
    .badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:500}
    .b-warn{background:rgba(245,158,11,.15);color:#fbbf24}
    .b-danger{background:rgba(239,68,68,.15);color:#f87171}
    .b-info{background:rgba(37,99,235,.15);color:#60a5fa}
    .b-ok{background:rgba(34,197,94,.15);color:#86efac}
    .alerts{max-height:65vh;overflow:auto;display:flex;flex-direction:column;gap:10px}
    .alert{padding:10px 12px;border:1px solid #1f2937;border-radius:10px;background:#0f172a;transition:all 0.2s}
    .alert.new{background:#1e293b;border-color:var(--accent)}
    .alert .row{display:flex;gap:8px;align-items:center;justify-content:space-between}
    .filters{display:flex;gap:8px;flex-wrap:wrap;font-size:14px}
    .muted{color:var(--muted);font-size:13px}
    .metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin-bottom:12px}
    .metric{background:#0f172a;padding:10px;border-radius:8px;text-align:center}
    .metric .value{font-size:24px;font-weight:bold;color:var(--accent)}
    .metric .label{font-size:12px;color:var(--muted);margin-top:4px}
    .ws-status{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
    .ws-status.connected{background:var(--ok)}
    .ws-status.disconnected{background:var(--danger)}
    .export-btn{background:var(--ok);border-color:#16a34a}
    @keyframes slideIn{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}
    @keyframes slideOut{from{opacity:1;transform:scale(1)}to{opacity:0;transform:scale(0.9)}}
  </style>
</head>
<body>
  <header>
    <h3>🚗 Road Tracker Pro</h3>
    <div>
      <span class="ws-status" id="wsStatus"></span>
      <span class="muted" id="wsLabel">WebSocket</span>
    </div>
  </header>
  <main>
    <div class="panel" style="margin-bottom:16px">
      <div class="head"><div>Controls</div></div>
      <div class="body">
        <div class="controls">
          <input id="source" type="text" placeholder="0 (webcam) or /path/to/video.mp4" />
          <button class="primary" onclick="start()">▶ Start</button>
          <button onclick="stopProc()">⏹ Stop</button>
          <label>Signal</label>
          <select id="signal"><option>green</option><option>red</option></select>
          <button onclick="setSignal()">Apply</button>
          <button class="export-btn" onclick="exportAlerts()">📥 Export CSV</button>
        </div>
      </div>
    </div>
    
    <div class="panel" style="margin-bottom:16px">
      <div class="head"><div>Performance Metrics</div></div>
      <div class="body">
        <div class="metrics" id="metrics"></div>
      </div>
    </div>
    
    <div style="display:grid;grid-template-columns:2fr 1fr 1fr;gap:16px">
      <div class="panel">
        <div class="head"><div>Live Stream</div></div>
        <div class="body"><img id="stream" src="/stream" /></div>
      </div>
      
      <div class="panel" style="background:#1a0a0a;border:3px solid var(--danger)">
        <div class="head" style="background:#2a0a0a;border-bottom:2px solid var(--danger)">
          <div style="color:var(--danger);font-weight:bold">🚨 VIOLATORS (<span id="violatorCount">0</span>)</div>
        </div>
        <div class="body" style="min-height:400px;max-height:70vh;overflow-y:auto">
          <div id="violatorGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;padding:8px">
            <p style="text-align:center;color:var(--muted);margin-top:60px;grid-column:1/-1">Waiting for violations...</p>
          </div>
        </div>
      </div>
      
      <div class="panel">
        <div class="head">
          <div>Alerts (<span id="alertCount">0</span>)</div>
          <div class="filters" style="font-size:11px">
            <label><input type="checkbox" class="flt" value="wrong_way" checked /> Wrong-Way</label>
            <label><input type="checkbox" class="flt" value="red_light_violation" checked /> Red Light</label>
            <label><input type="checkbox" class="flt" value="lane_violation" checked /> Lane</label>
            <label><input type="checkbox" class="flt" value="speeding" checked /> Speeding</label>
            <label><input type="checkbox" class="flt" value="no_helmet" checked /> No Helmet</label>
          </div>
        </div>
        <div class="body">
          <div id="alerts" class="alerts" style="max-height:55vh"></div>
        </div>
      </div>
    </div>
  </main>
  
  <script>
  let ws = null;
  let allAlerts = [];
  
  const typeBadge = (t)=>{
    const map={
      red_light_violation:['b-danger','🚦 Red Light'],
      lane_violation:['b-warn','⚠️ Lane'],
      speeding:['b-info','⚡ Speed'],
      wrong_way:['b-danger','🔄 Wrong-way'],
      no_helmet:['b-danger','🪖 No Helmet'],
      plate_read:['b-ok','🔢 Plate']
    };
    const m=map[t]||['b-info',t];
    return `<span class="badge ${m[0]}">${m[1]}</span>`;
  };
  
  function fmt(ts){
    try{ const d=new Date(ts*1000);return d.toLocaleTimeString(); }catch(e){ return '' }
  }
  
  function selectedTypes(){
    return new Set(Array.from(document.querySelectorAll('.flt')).filter(el=>el.checked).map(el=>el.value));
  }
  
  async function start(){
    const source = document.getElementById('source').value || 0;
    await fetch('/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:isNaN(Number(source))?source:Number(source)})});
    document.getElementById('stream').src='/stream?ts='+Date.now();
  }
  
  async function stopProc(){ await fetch('/stop',{method:'POST'}); }
  async function setSignal(){ const s=document.getElementById('signal').value; await fetch('/signal',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({state:s})}); }
  
  function connectWS(){
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${window.location.host}/ws/alerts`);
    
    ws.onopen = ()=>{
      document.getElementById('wsStatus').classList.add('connected');
      document.getElementById('wsStatus').classList.remove('disconnected');
      document.getElementById('wsLabel').textContent = 'Connected';
    };
    
    ws.onclose = ()=>{
      document.getElementById('wsStatus').classList.remove('connected');
      document.getElementById('wsStatus').classList.add('disconnected');
      document.getElementById('wsLabel').textContent = 'Disconnected';
      setTimeout(connectWS, 3000);
    };
    
    ws.onmessage = (e)=>{
      const alert = JSON.parse(e.data);
      allAlerts.unshift(alert);
      if(allAlerts.length > 200) allAlerts = allAlerts.slice(0, 200);
      renderAlerts();
      
      // Show violator in big panel (exclude plate_read)
      if(alert.type !== 'plate_read' && alert.evidence_id){
        showViolator(alert);
      }
    };
  }
  
  function renderAlerts(){
    const types = selectedTypes();
    const wrap = document.getElementById('alerts');
    const filtered = allAlerts.filter(a => types.has(a.type));
    
    document.getElementById('alertCount').textContent = filtered.length;
    
    wrap.innerHTML = '';
    for(const a of filtered.slice(0, 50)){
      const t=fmt(a.ts);
      const content = JSON.stringify(a.info || {});
      const evidence = a.evidence_id ? `<a href="/evidence/${a.evidence_id}" target="_blank" style="color:var(--accent)">View Evidence</a>` : '';
      const html = `
        <div class="alert">
          <div class="row">
            <div>${typeBadge(a.type)}</div>
            <div class="muted">${t}</div>
          </div>
          <div class="muted">Track: #${a.track_id ?? '-'}</div>
          <div style="margin-top:4px;font-size:13px">${content}</div>
          ${evidence ? `<div style="margin-top:6px">${evidence}</div>` : ''}
        </div>`;
      wrap.insertAdjacentHTML('beforeend', html);
    }
  }
  
  async function pollMetrics(){
    try{
      const r = await fetch('/metrics');
      const m = await r.json();
      const html = `
        <div class="metric"><div class="value">${m.fps}</div><div class="label">FPS</div></div>
        <div class="metric"><div class="value">${m.avg_detections}</div><div class="label">Detections</div></div>
        <div class="metric"><div class="value">${Object.values(m.violations).reduce((a,b)=>a+b,0)}</div><div class="label">Violations</div></div>
        <div class="metric"><div class="value">${Math.floor(m.uptime_seconds/60)}</div><div class="label">Uptime (min)</div></div>
      `;
      document.getElementById('metrics').innerHTML = html;
    }catch(e){}
    finally{ setTimeout(pollMetrics, 2000); }
  }
  
  let violatorQueue = [];
  let violatorTimers = {};
  
  function showViolator(alert){
    if(!alert.evidence_id) return;
    
    // Only show violations (not plate_read informational alerts)
    // Only show violations that get red "VIOLATED" label
    if(alert.type === 'plate_read') return;
    
    // Prevent duplicate alerts for same track+type
    const key = `${alert.track_id}_${alert.type}`;
    if(violatorQueue.some(v => `${v.track_id}_${v.type}` === key)){
      return; // Already showing this violation
    }
    
    // Add to queue
    violatorQueue.push(alert);
    updateViolatorCount();
    
    // Schedule removal after 5 seconds (matches red circle duration)
    const timeoutId = setTimeout(()=>{
      removeViolator(alert.evidence_id);
    }, 5000);
    
    violatorTimers[alert.evidence_id] = timeoutId;
    
    renderViolators();
  }
  
  function removeViolator(evidenceId){
    // Animate out
    const card = document.querySelector(`.violator-card[data-id="${evidenceId}"]`);
    if(card){
      card.style.animation = 'slideOut 0.3s ease';
      setTimeout(()=>{
        // Remove from queue
        violatorQueue = violatorQueue.filter(v => v.evidence_id !== evidenceId);
        
        // Clear timer
        if(violatorTimers[evidenceId]){
          clearTimeout(violatorTimers[evidenceId]);
          delete violatorTimers[evidenceId];
        }
        
        updateViolatorCount();
        renderViolators();
      }, 300);
    } else {
      // Card already gone, just clean up
      violatorQueue = violatorQueue.filter(v => v.evidence_id !== evidenceId);
      if(violatorTimers[evidenceId]){
        clearTimeout(violatorTimers[evidenceId]);
        delete violatorTimers[evidenceId];
      }
      updateViolatorCount();
      renderViolators();
    }
  }
  
  function updateViolatorCount(){
    document.getElementById('violatorCount').textContent = violatorQueue.length;
  }
  
  function renderViolators(){
    const grid = document.getElementById('violatorGrid');
    
    if(violatorQueue.length === 0){
      grid.innerHTML = '<p style="text-align:center;color:var(--muted);margin-top:60px;grid-column:1/-1">Waiting for violations...</p>';
      return;
    }
    
    grid.innerHTML = '';
    
    // Show all violators in responsive grid
    for(const alert of violatorQueue){
      const typeMap = {
        wrong_way: '🔄 WRONG-WAY',
        red_light_violation: '🚦 RED LIGHT',
        lane_violation: '⚠️ LANE',
        speeding: '⚡ SPEEDING',
        no_helmet: '🪖 NO HELMET'
      };
      
      const violationType = typeMap[alert.type] || alert.type.toUpperCase();
      
      // Build details
      const detailParts = [];
      if(alert.vehicle_class && alert.vehicle_class !== 'obj'){
        const vtype = alert.vehicle_class.charAt(0).toUpperCase() + alert.vehicle_class.slice(1);
        detailParts.push(`🚗 ${vtype}`);
      }
      detailParts.push(`#${alert.track_id}`);
      if(alert.info.plate) detailParts.push(`🔢 ${alert.info.plate}`);
      
      const details = detailParts.join(' • ');
      const cropPath = `/violations/crops/${alert.evidence_id}.jpg?t=${Date.now()}`;
      
      const cardHtml = `
        <div class="violator-card" data-id="${alert.evidence_id}" style="background:#0f0a0a;border:2px solid var(--danger);border-radius:8px;padding:8px;animation:slideIn 0.3s ease">
          <img src="${cropPath}" style="width:100%;height:auto;object-fit:contain;border:3px solid var(--danger);border-radius:6px;margin-bottom:6px;max-height:180px" onerror="this.style.display='none'" />
          <div style="font-weight:bold;color:var(--danger);font-size:13px;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${violationType}</div>
          <div style="color:var(--text);font-size:11px;line-height:1.4">${details}</div>
        </div>
      `;
      
      grid.insertAdjacentHTML('beforeend', cardHtml);
    }
  }
  
  function exportAlerts(){
    const types = selectedTypes();
    const filtered = allAlerts.filter(a => types.has(a.type));
    let csv = 'Timestamp,Type,Track ID,Info\\n';
    for(const a of filtered){
      const ts = new Date(a.ts * 1000).toISOString();
      const info = JSON.stringify(a.info).replace(/"/g, '""');
      csv += `"${ts}","${a.type}","${a.track_id}","${info}"\\n`;
    }
    const blob = new Blob([csv], {type:'text/csv'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `violations_${Date.now()}.csv`;
    a.click();
  }
  
  // Poll alerts as fallback (also updates violator panel)
  let lastAlertTs = 0;
  async function pollAlerts(){
    try{
      const r = await fetch('/alerts');
      const j = await r.json();
      const newAlerts = (j.alerts || []).filter(a => a.ts > lastAlertTs);
      
      if(newAlerts.length > 0){
        // Update allAlerts
        for(const a of newAlerts.reverse()){
          allAlerts.unshift(a);
          // Show violator if evidence exists
          if(a.type !== 'plate_read' && a.evidence_id){
            showViolator(a);
          }
        }
        if(allAlerts.length > 200) allAlerts = allAlerts.slice(0, 200);
        renderAlerts();
        lastAlertTs = Math.max(...newAlerts.map(a => a.ts));
      }
    }catch(e){}
    finally{ setTimeout(pollAlerts, 1000); }
  }
  
  document.querySelectorAll('.flt').forEach(el => el.addEventListener('change', renderAlerts));
  
  connectWS();
  pollMetrics();
  pollAlerts();  // Also poll for violator display
  </script>
</body>
</html>
"""


@app.post("/start")
async def start(req: StartRequest) -> Dict[str, Any]:
    """Start video processing."""
    proc = get_processor()
    ok = proc.start(req.source)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to open video source")
    logger.info(f"Started processing from {req.source}")
    return {"status": "started", "source": req.source}


@app.post("/stop")
async def stop() -> Dict[str, Any]:
    """Stop video processing."""
    proc = get_processor()
    proc.stop()
    logger.info("Stopped processing")
    return {"status": "stopped"}


@app.post("/signal")
async def set_signal(req: SignalRequest) -> Dict[str, Any]:
    """Set traffic signal state."""
    proc = get_processor()
    proc.set_signal_state(req.state)
    return {"state": proc.get_signal_state()}


@app.get("/alerts")
async def alerts() -> JSONResponse:
    """Get recent alerts."""
    proc = get_processor()
    return JSONResponse(proc.get_recent_alerts())


@app.get("/metrics")
async def metrics() -> JSONResponse:
    """Get performance metrics."""
    proc = get_processor()
    return JSONResponse(proc.get_metrics())


@app.get("/evidence/recent")
async def recent_evidence(limit: int = 50) -> JSONResponse:
    """Get recent violation evidence."""
    proc = get_processor()
    violations = proc.evidence_manager.get_recent_violations(limit)
    return JSONResponse({"violations": violations})


@app.get("/evidence/{evidence_id}")
async def get_evidence(evidence_id: str) -> JSONResponse:
    """Get specific evidence details."""
    proc = get_processor()
    meta_path = proc.evidence_manager.base_dir / "metadata" / f"{evidence_id}.json"
    
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    with open(meta_path, 'r') as f:
        metadata = json.load(f)
    
    return JSONResponse(metadata)


@app.get("/stream")
async def stream() -> StreamingResponse:
    """MJPEG video stream."""
    proc = get_processor()
    return StreamingResponse(
        proc.mjpeg_generator(), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket endpoint for real-time alerts."""
    await websocket.accept()
    with _ws_lock:
        _ws_clients.append(websocket)
    logger.info(f"WebSocket client connected. Total: {len(_ws_clients)}")
    
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        with _ws_lock:
            if websocket in _ws_clients:
                _ws_clients.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(_ws_clients)}")


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("Road Tracker Pro v2.0.0 starting...")
    
    # Pre-initialize processor
    get_processor()
    
    logger.info("Startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down...")
    if _processor:
        _processor.stop()
    logger.info("Shutdown complete")


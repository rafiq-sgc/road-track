# Public Display Layout Guide

## New 3-Column Layout

Your UI now has a dedicated **VIOLATOR panel** perfect for public awareness!

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 🚗 Road Tracker Pro                              [●] WebSocket Connected │
├──────────────────────────────────────────────────────────────────────────┤
│ Controls: [/path/video.mp4] [▶ Start] [⏹ Stop] Signal:[green▼] [📥 CSV]│
├──────────────────────────────────────────────────────────────────────────┤
│ Metrics: │ 10.2 FPS │ 12 Detections │ 5 Violations │ 45 min Uptime │    │
├──────────────────────────────────────────────────────────────────────────┤
│                    │                                │                     │
│  LIVE STREAM       │   🚨 VIOLATOR PANEL 🚨        │   ALERTS LIST       │
│  (2 columns wide)  │   (1 column - BIG!)           │   (1 column)        │
│                    │                                │                     │
│  ┌───────────────┐ │ ╔══════════════════════════╗  │ ┌─────────────┐   │
│  │               │ │ ║                          ║  │ │ 🔄 Wrong-way│   │
│  │  [Main video  │ │ ║   [LARGE CROP IMAGE]    ║  │ │ 10:58:00    │   │
│  │   with all    │ │ ║                          ║  │ │ Track #42   │   │
│  │   vehicles]   │ │ ║   🚗 Zoomed 3-5x        ║  │ └─────────────┘   │
│  │               │ │ ║                          ║  │ ┌─────────────┐   │
│  │   FPS: 10.2   │ │ ║   Red border            ║  │ │ 🚦 Red Light│   │
│  └───────────────┘ │ ╚══════════════════════════╝  │ │ 10:57:45    │   │
│                    │                                │ │ Track #15   │   │
│                    │ 🔄 WRONG-WAY VIOLATION         │ └─────────────┘   │
│                    │ Track #42 • Lane 0 • 10:58:00  │ ...more...        │
│                    │                                │                     │
└────────────────────┴────────────────────────────────┴─────────────────────┘
       50% width            25% width                      25% width
```

---

## How It Works

### When Violation Occurs

1. **Detection**: System detects wrong-way vehicle (Track #42)
2. **Evidence**: Auto-saves crop to `violations/crops/`
3. **Alert**: Sends via WebSocket with `evidence_id`
4. **Display**: JavaScript immediately:
   - Loads crop image from `/violations/crops/{evidence_id}.jpg`
   - Shows in center VIOLATOR panel (large!)
   - Displays violation type as big red text
   - Shows track #, lane, time
5. **Duration**: Stays visible for 8 seconds
6. **Auto-clear**: Clears and shows "Waiting for violation..."

---

## Panel Details

### Center Panel: VIOLATOR (Main Feature)

**Visual Design**:
- Dark red background (#1a0a0a)
- Red border (3px thick)
- Red header with 🚨 icon
- Large image area (400px+ height)

**Content**:
```
╔══════════════════════════════╗
║  🚨 VIOLATOR                 ║ ← Red header
╠══════════════════════════════╣
║                              ║
║   ┌────────────────────┐     ║
║   │                    │     ║
║   │   [LARGE IMAGE]    │     ║ ← Saved crop, 4px red border
║   │    of violator     │     ║
║   │                    │     ║
║   └────────────────────┘     ║
║                              ║
║  🔄 WRONG-WAY VIOLATION      ║ ← Violation type (big, bold)
║                              ║
║  Track #42 • Lane 0 • 10:58  ║ ← Details
║                              ║
╚══════════════════════════════╝
```

### Idle State (No Violations)
```
╔══════════════════════════════╗
║  🚨 VIOLATOR                 ║
╠══════════════════════════════╣
║                              ║
║                              ║
║   Waiting for violation...   ║
║                              ║
║                              ║
╚══════════════════════════════╝
```

---

## Perfect for Public Awareness

### Display on Large Screen (50-70 inches)

```
Public sees:
┌─────────────────────────────────────────────────┐
│                                                 │
│  Left: Live traffic (know where they are)      │
│                                                 │
│  Center: BIG VIOLATOR IMAGE (see who it is!)   │
│         ↑ THIS is what grabs attention         │
│                                                 │
│  Right: Alert history (see patterns)            │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Psychology**:
1. People see themselves (or their vehicle) BIG on screen
2. Clear "VIOLATED" message
3. Embarrassment/awareness leads to behavior change
4. Reduces future violations

---

## Customization Options

### Make Violator Panel Larger

In `main_v2.py`, change grid columns:
```html
<!-- Current: 2fr 1fr 1fr -->
<div style="display:grid;grid-template-columns:1.5fr 1.5fr 1fr;gap:16px">
```

Result: Live stream smaller, violator panel larger

### Make Violator Panel Full-Screen on Violation

Add to `showViolator()`:
```javascript
// Temporarily hide other panels
document.querySelector('.grid > :first-child').style.display = 'none';  // Hide stream
document.querySelector('.grid > :last-child').style.display = 'none';   // Hide alerts
// Center panel becomes full width

// Restore after 8s
setTimeout(() => {
  document.querySelector('.grid > :first-child').style.display = 'block';
  document.querySelector('.grid > :last-child').style.display = 'block';
}, 8000);
```

### Add Blinking Border

```javascript
// In CSS, add animation
@keyframes blink { 0%, 100% { border-color: red; } 50% { border-color: yellow; } }
.violator-panel { animation: blink 1s infinite; }
```

### Add Sound Alert

```javascript
// Play sound when violation shows
const audio = new Audio('/static/alert.wav');
audio.play();
```

---

## Image Quality

### Crop Size
- Original bbox size (varies by object size)
- Displayed at full size (no scaling down)
- Red border adds visual emphasis
- JPEG quality 90 (high detail)

### If Image is Blurry
Problem: Small object, low resolution

Solution 1: Increase crop padding in `evidence.py`:
```python
# Add padding around bbox
pad = 20
crop = frame[max(0, y1-pad):min(h, y2+pad), 
            max(0, x1-pad):min(w, x2+pad)]
```

Solution 2: Use higher JPEG quality:
```python
cv2.imwrite(str(crop_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])  # From 90
```

---

## Layout Variations

### For Small Screens (Laptop)

```
Stack vertically:
<div style="display:flex;flex-direction:column;gap:16px">
  <div>Live Stream (full width)</div>
  <div style="display:grid;grid-template-columns:1fr 1fr">
    <div>VIOLATOR</div>
    <div>Alerts</div>
  </div>
</div>
```

### For Public Display (Large Screen)

```
Current 3-column (perfect):
┌──────────┬───────────┬─────────┐
│  Stream  │ VIOLATOR  │ Alerts  │
│  (50%)   │  (25%)    │ (25%)   │
└──────────┴───────────┴─────────┘
```

### For Control Room (Multi-Monitor)

Monitor 1: Stream only
Monitor 2: Violator + Alerts
Monitor 3: Metrics + Charts

---

## Testing

### Step 1: Restart Server
```bash
uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Open UI
http://localhost:8000

You should see **three columns**:
- Left: Live Stream (largest)
- Center: VIOLATOR panel (red border, dark background)
- Right: Alerts list (compact)

### Step 3: Trigger Violation
- Start video
- Wait for wrong-way or any violation
- Watch center panel!

### Step 4: Verify
- ✅ Large crop image appears in center panel
- ✅ Red border around image
- ✅ Violation type in big red text
- ✅ Track #, lane, time shown below
- ✅ Image stays for 8 seconds
- ✅ Clears automatically

---

## For Maximum Impact (Public Display)

### Recommended Settings

1. **Fullscreen Browser** (F11)
2. **Dark Theme** (already applied)
3. **Auto-learning Enabled** (minimal setup)
4. **Large Monitor** (50"+ for best effect)
5. **High Brightness** (for outdoor/daylight viewing)

### Optional Enhancements

1. **Hide Controls**: Remove controls panel for cleaner look
2. **Larger Violator Panel**: Adjust grid columns
3. **Add Sound**: Play beep on violation
4. **Add Counter**: Show "Today: X violations"
5. **Auto-Loop Video**: Restart video when ends

---

## Summary

**What Changed**:
- ✅ Added dedicated VIOLATOR panel (center column)
- ✅ Shows large crop image of violator
- ✅ Red border, dark background for emphasis
- ✅ Big violation type text
- ✅ Track info and timestamp
- ✅ Auto-updates via WebSocket (instant)
- ✅ Auto-clears after 8 seconds
- ✅ Perfect for public display!

**Restart server and test!** Violators will now be displayed in a large, impossible-to-miss panel! 🎉


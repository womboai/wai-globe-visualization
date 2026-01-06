# W.AI Globe Visualization

Real-time 3D globe visualization of the W.AI distributed compute network.

**Live Demo**: https://visualizations-two.vercel.app

![W.AI Globe](https://img.shields.io/badge/nodes-1300+-00ff88) ![Cities](https://img.shields.io/badge/cities-200+-00ff88) ![Countries](https://img.shields.io/badge/countries-45+-00ff88)

---

## Overview

This visualization shows the W.AI network in real-time:
- **Active nodes** contributing compute power worldwide
- **Geographic distribution** across cities and countries
- **Task completion rate** (tasks per second)
- **Animated arcs** showing network activity between nodes

### Features

- **Real-time data** — Fetches network stats every 15 seconds from ClickHouse
- **Interactive globe** — Zoom, pan, auto-rotate
- **Ambient audio** — Pentatonic task ticks, ambient pads, chord chimes on data updates
- **Responsive stats** — Flash animations when values change
- **iOS compatible** — Audio works on mobile Safari

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Globe rendering | [Globe.gl](https://globe.gl/) v2.27.0 |
| 3D engine | [Three.js](https://threejs.org/) v0.160.0 |
| Audio | Web Audio API |
| Backend | Python serverless function |
| Data source | ClickHouse (via Grafana proxy) |
| Hosting | Vercel |

---

## Project Structure

```
wai-globe-visualization/
├── index.html          # Main visualization (single-file app)
├── api/
│   └── data.py         # Vercel serverless function for data
├── vercel.json         # Vercel configuration
├── requirements.txt    # Python dependencies
└── README.md
```

---

## Local Development

### Prerequisites

- Python 3.8+
- Access to Grafana (credentials in `api/data.py`)

### Running Locally

```bash
# Start local server
python3 -m http.server 8080

# Or use the included server script (if you have one)
python3 server.py
```

Then visit: http://localhost:8080

**Note**: For local development with live data, you'll need to run a local API server or modify `index.html` to point to the production API.

### Local API Server

Create a `server.py` for local development:

```python
#!/usr/bin/env python3
import json
import http.server
import socketserver
import urllib.request
import base64
import ssl

PORT = 8080

# Copy the data fetching functions from api/data.py here
# ... (see api/data.py for implementation)

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            # Return data JSON
            pass
        else:
            super().do_GET()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()
```

---

## Deployment

### Vercel (Current)

The app is deployed to Vercel with automatic deployments on push.

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Deploy to production
vercel --prod
```

### Environment Variables

Currently, Grafana credentials are hardcoded in `api/data.py`. For better security:

```bash
vercel env add GRAFANA_USER
vercel env add GRAFANA_PASS
```

Then update `api/data.py` to use `os.environ.get()`.

---

## API Reference

### GET /api/data

Returns current network statistics.

**Response:**

```json
{
  "cities": [
    {"city": "Seoul", "country": "KR", "workers": 142},
    {"city": "Ho Chi Minh City", "country": "VN", "workers": 89},
    ...
  ],
  "total_active": 1356,
  "total_cities": 212,
  "total_countries": 45,
  "tasks_per_second": 44.3
}
```

**Data Source**: ClickHouse `gateway_analytics` database via Grafana proxy.

**Refresh Rate**: Data is cached for 10 seconds (`s-maxage=10, stale-while-revalidate`).

---

## Data Pipeline

```
ClickHouse (gateway_analytics)
       ↓
   Grafana Proxy (auth)
       ↓
   Vercel Serverless Function (api/data.py)
       ↓
   Frontend (index.html)
```

### Key Queries

**Active workers by city (last 1 hour):**
```sql
SELECT w.geo_city, w.geo_country, count(DISTINCT w.id) AS workers
FROM gateway_analytics.tasks t
JOIN gateway_analytics.workers_analytics w FINAL ON w.id = t.worker_id
WHERE t.created_at >= now() - INTERVAL 1 HOUR
AND t.state IN ('in_progress', 'completed')
AND w._peerdb_is_deleted = 0
AND w.geo_city != ''
GROUP BY w.geo_city, w.geo_country
ORDER BY workers DESC
```

**Tasks per second (last 30 seconds):**
```sql
SELECT count(*) / 30.0 AS tps
FROM gateway_analytics.tasks
WHERE created_at >= now() - INTERVAL 30 SECOND
AND state = 'completed'
```

---

## Design System

### Colors

| Name | Hex | Usage |
|------|-----|-------|
| Primary Green | `#00ff88` | Points, arcs, text, accents |
| Background | `#000000` | Page background |
| Globe Surface | `#020804` | Globe mesh color |
| Text Primary | `#00ff88` | Stats, labels |
| Text Muted | `rgba(0,255,136,0.3)` | Labels, timestamps |

### Typography

| Element | Font | Weight | Size |
|---------|------|--------|------|
| Logo | JetBrains Mono | 400 | 20px |
| Stat Values | JetBrains Mono | 200 | 32px |
| Labels | JetBrains Mono | 300 | 8px |
| Timestamp | JetBrains Mono | 300 | 9px |

### Visual Effects

- **Scanlines** — Subtle CRT effect (0.03 opacity)
- **Vignette** — Edge darkening (50% center transparent)
- **Corner accents** — Decorative frame corners
- **Update flash** — Green radial pulse on data change
- **Pulsing indicator** — Breathing animation on "LIVE" dot

---

## Audio System

### Task Ticks
- **Scale**: Pentatonic (A5-A6 range: 880Hz - 1760Hz)
- **Rate**: Proportional to TPS, capped at 4 ticks/second
- **Character**: Delicate, high-pitched, short decay

### Ambient Pads
- **Scale**: C3, E3, G3, A3 (130-220Hz)
- **Interval**: Every 3-5 seconds
- **Character**: Low, sustained, filtered

### Data Update Chime
- **Chord**: C4, E4, G4 (261-392Hz)
- **Trigger**: When total nodes changes
- **Character**: Soft, staggered arpeggio

### iOS Compatibility

iOS Safari requires:
1. AudioContext created **synchronously** in a user gesture handler
2. An oscillator **started immediately** in the same handler
3. Using `touchstart` event (not just `click`)

```javascript
document.addEventListener('touchstart', () => {
  audioCtx = new AudioContext();
  const osc = audioCtx.createOscillator();
  osc.connect(audioCtx.destination);
  osc.start(0);
  osc.stop(audioCtx.currentTime + 0.1);
}, { once: true });
```

---

## Geo Lookup

The visualization includes a hardcoded lookup table for city coordinates. Cities not in the lookup fall back to country centroids.

### Adding New Cities

Edit the `geoLookup` object in `index.html`:

```javascript
const geoLookup = {
  "City Name|CC": [latitude, longitude],
  // Example:
  "New York|US": [40.7128, -74.0060],
};
```

Format: `"City|CountryCode": [lat, lng]`

---

## Known Issues

1. **Audio on iOS** — Requires tap to enable (browser policy, not fixable)
2. **Missing cities** — Some cities not in lookup table fall back to country center
3. **Hardcoded credentials** — Grafana auth should move to env vars

---

## Roadmap / Ideas

- [ ] Add VRAM stat (requires new query)
- [ ] Add total tasks completed counter
- [ ] Heatmap mode toggle
- [ ] Time-lapse playback of historical data
- [ ] Embed-friendly version (no audio, smaller)
- [ ] React/Next.js component version for w.ai homepage

---

## Related Repositories

| Repo | Description |
|------|-------------|
| [w_ai](https://github.com/womboai/w_ai) | Core gateway + workers |
| [w_ai_web](https://github.com/womboai/w_ai_web) | Next.js portal |

---

## Context & History

This visualization was built on **January 2, 2026** as part of the W.AI branding push.

### Original Requirements
- Show real-time network activity
- Matrix/cyberpunk aesthetic
- Ambient soundscape that responds to network activity
- Mobile compatible

### Design Iterations
1. Initial version with basic Globe.gl setup
2. Added ambient audio system (pentatonic scale)
3. Fixed arc stuttering with lifecycle-based animation pool
4. Solved iOS audio through synchronous AudioContext creation
5. Deployed to Vercel with serverless API

---

## Credentials

**Grafana** (for data queries):
- URL: `https://grafana.wombo.tech`
- User: `admin`
- Pass: `WaiStrongPass`
- ClickHouse datasource UID: `deqrkzd6qp6o0c`

**Note**: These are currently hardcoded in `api/data.py`. Move to environment variables for production.

---

## License

Internal use only. Part of W.AI infrastructure.

#!/usr/bin/env python3
"""
W.AI Globe Visualization - Local Development Server
Serves the globe HTML and provides real-time metrics endpoint.

Usage:
    python3 server.py

Then visit: http://localhost:8080
"""

import json
import http.server
import socketserver
import urllib.request
import base64
import ssl
from pathlib import Path

PORT = 8080

# Grafana config
GRAFANA_URL = "https://grafana.wombo.tech"
GRAFANA_USER = "admin"
GRAFANA_PASS = "WaiStrongPass"
CH_DATASOURCE_UID = "deqrkzd6qp6o0c"

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


def query_clickhouse(sql: str) -> dict:
    """Run a ClickHouse query via Grafana's datasource proxy."""
    credentials = base64.b64encode(f"{GRAFANA_USER}:{GRAFANA_PASS}".encode()).decode()
    payload = {
        "queries": [{
            "refId": "A",
            "datasource": {"uid": CH_DATASOURCE_UID, "type": "grafana-clickhouse-datasource"},
            "rawSql": sql,
            "format": 1,
            "editorType": "sql",
            "queryType": "table"
        }],
        "from": "now-1h",
        "to": "now"
    }
    req = urllib.request.Request(
        f"{GRAFANA_URL}/api/ds/query",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as response:
        return json.loads(response.read().decode())


def get_live_data():
    """Fetch live city data from W.AI network."""
    sql = """
    SELECT w.geo_city, w.geo_country, count(DISTINCT w.id) AS workers
    FROM gateway_analytics.tasks t
    JOIN gateway_analytics.workers_analytics w FINAL ON w.id = t.worker_id
    WHERE t.created_at >= now() - INTERVAL 1 HOUR
    AND t.state IN ('in_progress', 'completed')
    AND w._peerdb_is_deleted = 0
    AND w.geo_city != ''
    AND w.geo_country != ''
    GROUP BY w.geo_city, w.geo_country
    ORDER BY workers DESC
    """
    try:
        resp = query_clickhouse(sql)
        frames = resp.get("results", {}).get("A", {}).get("frames", [])
        if frames and frames[0].get("data", {}).get("values"):
            values = frames[0]["data"]["values"]
            cities = values[0]
            countries = values[1]
            workers = values[2]
            return [{"city": cities[i], "country": countries[i], "workers": workers[i]}
                    for i in range(len(cities))]
    except Exception as e:
        print(f"Error fetching data: {e}")
    return []


def get_total_active():
    """Get total active workers (including unknown geo)."""
    sql = """
    SELECT count(DISTINCT w.id) AS workers
    FROM gateway_analytics.tasks t
    JOIN gateway_analytics.workers_analytics w FINAL ON w.id = t.worker_id
    WHERE t.created_at >= now() - INTERVAL 1 HOUR
    AND t.state IN ('in_progress', 'completed')
    AND w._peerdb_is_deleted = 0
    """
    try:
        resp = query_clickhouse(sql)
        frames = resp.get("results", {}).get("A", {}).get("frames", [])
        if frames and frames[0].get("data", {}).get("values"):
            return frames[0]["data"]["values"][0][0]
    except Exception as e:
        print(f"Error fetching total: {e}")
    return 0


def get_tasks_per_second():
    """Get task completion rate (tasks per second over last 30s)."""
    sql = """
    SELECT count(*) / 30.0 AS tps
    FROM gateway_analytics.tasks
    WHERE created_at >= now() - INTERVAL 30 SECOND
    AND state = 'completed'
    """
    try:
        resp = query_clickhouse(sql)
        frames = resp.get("results", {}).get("A", {}).get("frames", [])
        if frames and frames[0].get("data", {}).get("values"):
            return round(frames[0]["data"]["values"][0][0], 2)
    except Exception as e:
        print(f"Error fetching TPS: {e}")
    return 0


class ReuseAddrTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            cities = get_live_data()
            total = get_total_active()
            tps = get_tasks_per_second()

            data = {
                "cities": cities,
                "total_active": total,
                "total_cities": len(cities),
                "total_countries": len(set(c["country"] for c in cities)),
                "tasks_per_second": tps
            }
            self.wfile.write(json.dumps(data).encode())
        else:
            super().do_GET()


if __name__ == "__main__":
    print(f"Starting W.AI Globe Visualization server...")
    print(f"Visit: http://localhost:{PORT}")
    print(f"API endpoint: http://localhost:{PORT}/api/data")
    print(f"Press Ctrl+C to stop.\n")

    with ReuseAddrTCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")

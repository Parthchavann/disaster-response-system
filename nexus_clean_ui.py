#!/usr/bin/env python3
"""
NEXUS Clean UI - Professional Disaster Response Dashboard
Minimalist, Clean, and Professional Design
"""

import http.server
import socketserver
import json
import time
import random
from datetime import datetime, timedelta
import requests
import logging
import threading
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CleanDataProcessor:
    def __init__(self):
        self.cache = {}
        self.last_update = {}
        self.cache_duration = 30
        self.alerts = []
        
    def get_cached_or_fetch(self, key, fetch_func, force_refresh=False):
        now = datetime.now()
        
        if (key in self.cache and 
            key in self.last_update and 
            not force_refresh and
            (now - self.last_update[key]).seconds < self.cache_duration):
            return self.cache[key]
        
        try:
            data = fetch_func()
            self.cache[key] = data
            self.last_update[key] = now
            
            if key == 'earthquakes' and data:
                self.check_for_alerts(data)
            
            return data
        except Exception as e:
            logger.error(f"Error fetching {key}: {e}")
            return self.cache.get(key, [])
    
    def check_for_alerts(self, earthquakes):
        """Generate alerts for significant earthquakes"""
        for eq in earthquakes:
            if eq.get('magnitude', 0) >= 5.0:
                alert = {
                    'id': eq['id'],
                    'type': 'major' if eq['magnitude'] >= 6.0 else 'moderate',
                    'message': f"Magnitude {eq['magnitude']} earthquake near {eq['location']}",
                    'timestamp': datetime.now().isoformat(),
                    'details': eq
                }
                
                if not any(a['id'] == alert['id'] for a in self.alerts):
                    self.alerts.insert(0, alert)
                    self.alerts = self.alerts[:10]
    
    def fetch_earthquakes(self):
        def _fetch():
            all_earthquakes = []
            
            endpoints = [
                ("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson", "4.5+ magnitude"),
                ("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson", "2.5+ magnitude"),
                ("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson", "significant")
            ]
            
            for url, description in endpoints:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        for feature in data.get('features', []):
                            props = feature.get('properties', {})
                            coords = feature.get('geometry', {}).get('coordinates', [0, 0, 0])
                            
                            eq_id = feature.get('id')
                            if any(eq['id'] == eq_id for eq in all_earthquakes):
                                continue
                            
                            mag = props.get('mag')
                            if mag is None:
                                continue
                            
                            earthquake = {
                                'id': eq_id,
                                'magnitude': float(mag),
                                'location': str(props.get('place', 'Unknown Location')),
                                'time': props.get('time', int(time.time() * 1000)),
                                'depth': float(coords[2]) if coords[2] else 0.0,
                                'latitude': float(coords[1]) if coords[1] else 0.0,
                                'longitude': float(coords[0]) if coords[0] else 0.0,
                                'mag_type': str(props.get('magType', 'unknown')),
                                'significance': int(props.get('sig', 0)) if props.get('sig') else 0,
                                'felt_reports': int(props.get('felt', 0)) if props.get('felt') else 0,
                                'alert': str(props.get('alert', 'green')) if props.get('alert') else 'green',
                                'tsunami': int(props.get('tsunami', 0)) if props.get('tsunami') else 0,
                                'url': str(props.get('url', ''))
                            }
                            all_earthquakes.append(earthquake)
                        
                        logger.info(f"✅ Fetched {len(all_earthquakes)} from {description} feed")
                except Exception as e:
                    logger.warning(f"Failed to fetch from {description}: {e}")
            
            all_earthquakes.sort(key=lambda x: x['time'], reverse=True)
            return all_earthquakes[:100]
        
        return self.get_cached_or_fetch('earthquakes', _fetch)
    
    def get_statistics(self):
        earthquakes = self.fetch_earthquakes()
        now = datetime.now()
        
        one_hour_ago = (now - timedelta(hours=1)).timestamp() * 1000
        six_hours_ago = (now - timedelta(hours=6)).timestamp() * 1000
        day_ago = (now - timedelta(days=1)).timestamp() * 1000
        
        stats = {
            'total_events': len(earthquakes),
            'major_events': len([eq for eq in earthquakes if eq.get('magnitude', 0) >= 5.0]),
            'moderate_events': len([eq for eq in earthquakes if 3.0 <= eq.get('magnitude', 0) < 5.0]),
            'minor_events': len([eq for eq in earthquakes if eq.get('magnitude', 0) < 3.0]),
            'tsunami_alerts': len([eq for eq in earthquakes if eq.get('tsunami', 0) == 1]),
            'last_hour': len([eq for eq in earthquakes if eq.get('time', 0) > one_hour_ago]),
            'last_6_hours': len([eq for eq in earthquakes if eq.get('time', 0) > six_hours_ago]),
            'last_24_hours': len([eq for eq in earthquakes if eq.get('time', 0) > day_ago]),
            'avg_magnitude': round(sum(eq.get('magnitude', 0) for eq in earthquakes) / len(earthquakes), 2) if earthquakes else 0,
            'max_magnitude': max((eq.get('magnitude', 0) for eq in earthquakes), default=0),
            'deepest': max((eq.get('depth', 0) for eq in earthquakes), default=0),
            'alerts_count': len(self.alerts),
            'last_update': now.isoformat()
        }
        
        regions = {}
        for eq in earthquakes:
            location = eq.get('location', '')
            for region in ['California', 'Alaska', 'Japan', 'Indonesia', 'Turkey', 'Greece', 'Chile', 'Mexico']:
                if region.lower() in location.lower():
                    regions[region] = regions.get(region, 0) + 1
                    break
            else:
                regions['Other'] = regions.get('Other', 0) + 1
        
        stats['regions'] = regions
        return stats

class CleanHTTPHandler(http.server.SimpleHTTPRequestHandler):
    data_processor = CleanDataProcessor()
    
    def do_GET(self):
        if self.path == '/' or self.path == '/dashboard':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            html_content = self.generate_dashboard_html()
            self.wfile.write(html_content.encode('utf-8'))
            
        elif self.path == '/api/events':
            self.send_json_response(self.data_processor.fetch_earthquakes())
            
        elif self.path == '/api/stats':
            self.send_json_response(self.data_processor.get_statistics())
            
        elif self.path == '/api/alerts':
            self.send_json_response(self.data_processor.alerts)
            
        elif self.path == '/api/health':
            self.send_json_response({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '4.0.0-clean'
            })
            
        else:
            self.send_error(404)
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode('utf-8'))
    
    def log_message(self, format, *args):
        pass
    
    def generate_dashboard_html(self):
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEXUS - Earthquake Monitoring Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f8fafc;
            color: #1e293b;
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        /* Header */
        .header {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }

        .logo-section {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .logo {
            width: 48px;
            height: 48px;
            background: #3b82f6;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 20px;
            font-weight: 700;
        }

        .title h1 {
            font-size: 24px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 4px;
        }

        .title p {
            color: #64748b;
            font-size: 14px;
        }

        .status-indicators {
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
        }

        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: #f1f5f9;
            border-radius: 6px;
            font-size: 13px;
            color: #475569;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
        }

        /* Controls */
        .controls {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
            flex-wrap: wrap;
            align-items: center;
        }

        .btn {
            padding: 8px 16px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            background: white;
            color: #374151;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
            text-decoration: none;
        }

        .btn:hover {
            background: #f9fafb;
            border-color: #9ca3af;
        }

        .btn-primary {
            background: #3b82f6;
            border-color: #3b82f6;
            color: white;
        }

        .btn-primary:hover {
            background: #2563eb;
            border-color: #2563eb;
        }

        .filter-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .filter-label {
            font-size: 14px;
            color: #6b7280;
            font-weight: 500;
        }

        .filter-select {
            padding: 6px 10px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            background: white;
            color: #374151;
            font-size: 14px;
            cursor: pointer;
        }

        /* Grid */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
            margin-bottom: 24px;
        }

        .grid-full {
            grid-column: 1 / -1;
        }

        /* Cards */
        .card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .card-title {
            font-size: 18px;
            font-weight: 600;
            color: #1e293b;
        }

        .card-actions {
            display: flex;
            gap: 8px;
        }

        .card-action {
            width: 32px;
            height: 32px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            color: #6b7280;
            font-size: 14px;
            transition: all 0.2s;
        }

        .card-action:hover {
            background: #f9fafb;
            color: #374151;
        }

        /* Statistics */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 16px;
        }

        .stat-item {
            text-align: center;
            padding: 16px;
            background: #f8fafc;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }

        .stat-value {
            font-size: 24px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 4px;
        }

        .stat-label {
            font-size: 12px;
            color: #64748b;
            font-weight: 500;
        }

        /* Map */
        .map-container {
            height: 400px;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #e2e8f0;
            position: relative;
        }

        .map-controls {
            position: absolute;
            top: 12px;
            right: 12px;
            z-index: 1000;
            display: flex;
            gap: 6px;
        }

        .map-control {
            padding: 6px 12px;
            background: white;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            color: #374151;
            font-weight: 500;
            transition: all 0.2s;
        }

        .map-control:hover,
        .map-control.active {
            background: #3b82f6;
            border-color: #3b82f6;
            color: white;
        }

        /* Charts */
        .chart-container {
            height: 300px;
            position: relative;
        }

        /* Events List */
        .events-list {
            max-height: 400px;
            overflow-y: auto;
        }

        .event-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            border-bottom: 1px solid #f1f5f9;
            transition: background 0.2s;
            cursor: pointer;
        }

        .event-item:hover {
            background: #f8fafc;
        }

        .event-item:last-child {
            border-bottom: none;
        }

        .magnitude-badge {
            min-width: 40px;
            height: 40px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 14px;
            color: white;
        }

        .mag-minor { background: #10b981; }
        .mag-light { background: #f59e0b; }
        .mag-moderate { background: #ef4444; }
        .mag-strong { background: #dc2626; }
        .mag-major { background: #7c3aed; }

        .event-details {
            flex: 1;
        }

        .event-location {
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 2px;
            font-size: 14px;
        }

        .event-meta {
            color: #64748b;
            font-size: 12px;
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }

        /* Alert */
        .alert {
            background: #fef3c7;
            border: 1px solid #f59e0b;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 16px;
            color: #92400e;
            font-size: 14px;
        }

        /* Loading */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px;
            color: #64748b;
        }

        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid #e2e8f0;
            border-left: 2px solid #3b82f6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 12px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 20px;
            color: #64748b;
            font-size: 14px;
            border-top: 1px solid #e2e8f0;
            margin-top: 40px;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .container { padding: 16px; }
            .header { padding: 16px; }
            .card { padding: 16px; }
            .grid { grid-template-columns: 1fr; }
            .header-content { text-align: center; }
            .controls { justify-content: center; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
        }

        ::-webkit-scrollbar-track {
            background: #f1f5f9;
        }

        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="header-content">
                <div class="logo-section">
                    <div class="logo">N</div>
                    <div class="title">
                        <h1>NEXUS Earthquake Monitor</h1>
                        <p>Real-time global earthquake tracking</p>
                    </div>
                </div>
                <div class="status-indicators">
                    <div class="status-item">
                        <div class="status-dot"></div>
                        <span>Live Data</span>
                    </div>
                    <div class="status-item">
                        <div class="status-dot" style="background: #f59e0b;"></div>
                        <span id="eventCount">0 Events</span>
                    </div>
                    <div class="status-item">
                        <div class="status-dot" style="background: #ef4444;"></div>
                        <span id="alertCount">0 Alerts</span>
                    </div>
                </div>
            </div>
        </header>

        <!-- Controls -->
        <div class="controls">
            <button class="btn btn-primary" onclick="refreshData()">
                ↻ Refresh
            </button>
            <button class="btn" id="autoBtn" onclick="toggleAutoRefresh()">
                ▶ Auto-Refresh
            </button>
            <button class="btn" onclick="toggleHeatmap()">
                🔥 Heatmap
            </button>
            <button class="btn" onclick="exportData()">
                ⬇ Export
            </button>
            
            <div class="filter-group">
                <span class="filter-label">Magnitude:</span>
                <select class="filter-select" id="magnitudeFilter" onchange="filterEvents()">
                    <option value="all">All</option>
                    <option value="2.5">2.5+</option>
                    <option value="4.0">4.0+</option>
                    <option value="5.0">5.0+</option>
                    <option value="6.0">6.0+</option>
                </select>
            </div>

            <div class="filter-group">
                <span class="filter-label">Time:</span>
                <select class="filter-select" id="timeFilter" onchange="filterEvents()">
                    <option value="all">All Time</option>
                    <option value="1">Last Hour</option>
                    <option value="6">Last 6 Hours</option>
                    <option value="24">Last 24 Hours</option>
                </select>
            </div>
        </div>

        <!-- Alerts -->
        <div id="alertsContainer"></div>

        <!-- Grid -->
        <div class="grid">
            <!-- Statistics -->
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">Statistics</h2>
                    <div class="card-actions">
                        <div class="card-action" onclick="refreshData()">↻</div>
                    </div>
                </div>
                <div class="stats-grid" id="statsGrid">
                    <div class="loading">
                        <div class="spinner"></div>
                        Loading...
                    </div>
                </div>
            </div>

            <!-- Magnitude Chart -->
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">Magnitude Distribution</h2>
                </div>
                <div class="chart-container">
                    <canvas id="magnitudeChart"></canvas>
                </div>
            </div>

            <!-- Map -->
            <div class="card grid-full">
                <div class="card-header">
                    <h2 class="card-title">Global Earthquake Map</h2>
                </div>
                <div class="map-container">
                    <div class="map-controls">
                        <div class="map-control active" onclick="toggleMapView('street')" id="streetBtn">Street</div>
                        <div class="map-control" onclick="toggleMapView('satellite')" id="satelliteBtn">Satellite</div>
                        <div class="map-control" onclick="toggleMapView('terrain')" id="terrainBtn">Terrain</div>
                    </div>
                    <div id="map" style="height: 100%;"></div>
                </div>
            </div>

            <!-- Recent Events -->
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">Recent Events</h2>
                    <div class="card-actions">
                        <div class="card-action" onclick="sortEvents('time')">⌚</div>
                        <div class="card-action" onclick="sortEvents('magnitude')">📊</div>
                    </div>
                </div>
                <div class="events-list" id="eventsList">
                    <div class="loading">
                        <div class="spinner"></div>
                        Loading events...
                    </div>
                </div>
            </div>

            <!-- Regional Chart -->
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">Regional Distribution</h2>
                </div>
                <div class="chart-container">
                    <canvas id="regionalChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <footer class="footer">
            <p>NEXUS Earthquake Monitor v4.0 | Real-time USGS Data | Last Updated: <span id="lastUpdate">--</span></p>
        </footer>
    </div>

    <script>
        let map;
        let magnitudeChart;
        let regionalChart;
        let heatmapLayer;
        let markers = [];
        let allEvents = [];
        let filteredEvents = [];
        let autoRefreshInterval;
        let isAutoRefreshing = false;
        let sortOrder = 'time';

        document.addEventListener('DOMContentLoaded', function() {
            initializeMap();
            initializeCharts();
            loadData();
            setInterval(loadData, 30000);
        });

        function initializeMap() {
            map = L.map('map').setView([20, 0], 2);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors',
                maxZoom: 18
            }).addTo(map);
        }

        function initializeCharts() {
            const magCtx = document.getElementById('magnitudeChart').getContext('2d');
            magnitudeChart = new Chart(magCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Minor (< 3.0)', 'Light (3.0-3.9)', 'Moderate (4.0-4.9)', 'Strong (5.0-5.9)', 'Major (6.0+)'],
                    datasets: [{
                        data: [0, 0, 0, 0, 0],
                        backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#dc2626', '#7c3aed'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: '#64748b',
                                padding: 15,
                                font: { family: 'Inter', size: 12 }
                            }
                        }
                    }
                }
            });

            const regCtx = document.getElementById('regionalChart').getContext('2d');
            regionalChart = new Chart(regCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Events',
                        data: [],
                        backgroundColor: '#3b82f6',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#f1f5f9' },
                            ticks: { color: '#64748b', font: { size: 11 } }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#64748b', font: { size: 11 } }
                        }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }

        async function loadData() {
            try {
                const [eventsResponse, statsResponse, alertsResponse] = await Promise.all([
                    fetch('/api/events'),
                    fetch('/api/stats'),
                    fetch('/api/alerts')
                ]);

                allEvents = await eventsResponse.json();
                const stats = await statsResponse.json();
                const alerts = await alertsResponse.json();

                updateStatistics(stats);
                filterEvents();
                updateMap();
                updateCharts();
                displayAlerts(alerts);

                document.getElementById('eventCount').textContent = `${allEvents.length} Events`;
                document.getElementById('alertCount').textContent = `${alerts.length} Alerts`;
                document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                console.error('Error loading data:', error);
            }
        }

        function updateStatistics(stats) {
            const statsGrid = document.getElementById('statsGrid');
            statsGrid.innerHTML = `
                <div class="stat-item">
                    <div class="stat-value">${stats.total_events}</div>
                    <div class="stat-label">Total Events</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${stats.major_events}</div>
                    <div class="stat-label">Major (5.0+)</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${stats.last_6_hours}</div>
                    <div class="stat-label">Last 6 Hours</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${stats.tsunami_alerts}</div>
                    <div class="stat-label">Tsunami Risk</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${stats.avg_magnitude}</div>
                    <div class="stat-label">Avg Magnitude</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${stats.max_magnitude}</div>
                    <div class="stat-label">Max Magnitude</div>
                </div>
            `;

            if (stats.regions) {
                const labels = Object.keys(stats.regions);
                const data = Object.values(stats.regions);
                regionalChart.data.labels = labels;
                regionalChart.data.datasets[0].data = data;
                regionalChart.update();
            }
        }

        function filterEvents() {
            const magFilter = parseFloat(document.getElementById('magnitudeFilter').value);
            const timeFilter = document.getElementById('timeFilter').value;
            
            filteredEvents = allEvents.filter(event => {
                if (!isNaN(magFilter) && event.magnitude < magFilter) {
                    return false;
                }
                
                if (timeFilter !== 'all') {
                    const hoursAgo = parseInt(timeFilter);
                    const cutoffTime = Date.now() - (hoursAgo * 60 * 60 * 1000);
                    if (event.time < cutoffTime) {
                        return false;
                    }
                }
                
                return true;
            });

            if (sortOrder === 'magnitude') {
                filteredEvents.sort((a, b) => b.magnitude - a.magnitude);
            } else {
                filteredEvents.sort((a, b) => b.time - a.time);
            }

            updateEventsList();
            updateMap();
            updateCharts();
        }

        function updateEventsList() {
            const eventsList = document.getElementById('eventsList');
            
            if (filteredEvents.length === 0) {
                eventsList.innerHTML = '<div class="loading">No events found</div>';
                return;
            }

            eventsList.innerHTML = filteredEvents.slice(0, 20).map(event => {
                const magnitude = event.magnitude || 0;
                const magClass = getMagnitudeClass(magnitude);
                const timeStr = new Date(event.time).toLocaleString();
                
                return `
                    <div class="event-item" onclick="focusEvent('${event.id}')">
                        <div class="magnitude-badge ${magClass}">
                            ${magnitude.toFixed(1)}
                        </div>
                        <div class="event-details">
                            <div class="event-location">${event.location}</div>
                            <div class="event-meta">
                                <span>⏰ ${timeStr}</span>
                                <span>📏 ${event.depth.toFixed(1)}km deep</span>
                                ${event.felt_reports > 0 ? `<span>👥 ${event.felt_reports} reports</span>` : ''}
                                ${event.tsunami ? '<span>🌊 Tsunami risk</span>' : ''}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function updateMap() {
            markers.forEach(marker => map.removeLayer(marker));
            markers = [];

            filteredEvents.forEach(event => {
                if (event.latitude && event.longitude) {
                    const magnitude = event.magnitude || 0;
                    const color = getMagnitudeColor(magnitude);
                    const size = Math.max(4, magnitude * 2);

                    const marker = L.circleMarker([event.latitude, event.longitude], {
                        radius: size,
                        fillColor: color,
                        color: 'white',
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.8
                    }).addTo(map);

                    const timeStr = new Date(event.time).toLocaleString();
                    marker.bindPopup(`
                        <div style="color: #374151; min-width: 200px;">
                            <strong style="font-size: 14px;">${event.location}</strong><br><br>
                            <strong>Magnitude:</strong> ${magnitude.toFixed(1)}<br>
                            <strong>Depth:</strong> ${event.depth.toFixed(1)}km<br>
                            <strong>Time:</strong> ${timeStr}<br>
                            ${event.felt_reports > 0 ? `<strong>Reports:</strong> ${event.felt_reports}<br>` : ''}
                            ${event.tsunami ? '<span style="color: #ef4444;">⚠️ Tsunami Risk</span><br>' : ''}
                            ${event.url ? `<br><a href="${event.url}" target="_blank" style="color: #3b82f6;">View Details →</a>` : ''}
                        </div>
                    `);

                    markers.push(marker);
                }
            });
        }

        function updateCharts() {
            const distribution = [0, 0, 0, 0, 0];
            
            filteredEvents.forEach(event => {
                const mag = event.magnitude || 0;
                if (mag < 3.0) distribution[0]++;
                else if (mag < 4.0) distribution[1]++;
                else if (mag < 5.0) distribution[2]++;
                else if (mag < 6.0) distribution[3]++;
                else distribution[4]++;
            });

            magnitudeChart.data.datasets[0].data = distribution;
            magnitudeChart.update();
        }

        function displayAlerts(alerts) {
            const container = document.getElementById('alertsContainer');
            
            if (alerts.length === 0) {
                container.innerHTML = '';
                return;
            }

            container.innerHTML = alerts.slice(0, 3).map(alert => `
                <div class="alert">
                    <strong>${alert.type === 'major' ? 'Major Earthquake Alert' : 'Earthquake Alert'}:</strong>
                    ${alert.message}
                </div>
            `).join('');
        }

        function getMagnitudeClass(magnitude) {
            if (magnitude < 3.0) return 'mag-minor';
            if (magnitude < 4.0) return 'mag-light';
            if (magnitude < 5.0) return 'mag-moderate';
            if (magnitude < 6.0) return 'mag-strong';
            return 'mag-major';
        }

        function getMagnitudeColor(magnitude) {
            if (magnitude < 3.0) return '#10b981';
            if (magnitude < 4.0) return '#f59e0b';
            if (magnitude < 5.0) return '#ef4444';
            if (magnitude < 6.0) return '#dc2626';
            return '#7c3aed';
        }

        function refreshData() {
            loadData();
        }

        function toggleAutoRefresh() {
            const btn = document.getElementById('autoBtn');
            
            if (isAutoRefreshing) {
                clearInterval(autoRefreshInterval);
                btn.textContent = '▶ Auto-Refresh';
                isAutoRefreshing = false;
            } else {
                autoRefreshInterval = setInterval(loadData, 10000);
                btn.textContent = '⏸ Stop Auto';
                isAutoRefreshing = true;
            }
        }

        function toggleHeatmap() {
            if (heatmapLayer) {
                map.removeLayer(heatmapLayer);
                heatmapLayer = null;
            } else {
                const heatData = filteredEvents.map(event => [
                    event.latitude,
                    event.longitude,
                    event.magnitude / 10
                ]);
                
                heatmapLayer = L.heatLayer(heatData, {
                    radius: 20,
                    blur: 10,
                    gradient: {
                        0.1: '#10b981',
                        0.3: '#f59e0b',
                        0.5: '#ef4444',
                        0.7: '#dc2626',
                        1.0: '#7c3aed'
                    }
                }).addTo(map);
            }
        }

        function toggleMapView(view) {
            document.querySelectorAll('.map-control').forEach(btn => btn.classList.remove('active'));
            document.getElementById(view + 'Btn').classList.add('active');
            
            map.eachLayer(layer => {
                if (layer instanceof L.TileLayer) {
                    map.removeLayer(layer);
                }
            });
            
            let tileUrl;
            switch(view) {
                case 'satellite':
                    tileUrl = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
                    break;
                case 'terrain':
                    tileUrl = 'https://stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}.png';
                    break;
                default:
                    tileUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
            }
            
            L.tileLayer(tileUrl, {
                attribution: '© Map contributors',
                maxZoom: 18
            }).addTo(map);
        }

        function sortEvents(by) {
            sortOrder = by;
            filterEvents();
        }

        function focusEvent(eventId) {
            const event = allEvents.find(e => e.id === eventId);
            if (event && event.latitude && event.longitude) {
                map.setView([event.latitude, event.longitude], 8);
                
                markers.forEach(marker => {
                    const latlng = marker.getLatLng();
                    if (Math.abs(latlng.lat - event.latitude) < 0.01 && 
                        Math.abs(latlng.lng - event.longitude) < 0.01) {
                        marker.openPopup();
                    }
                });
            }
        }

        function exportData() {
            const reportData = {
                generated: new Date().toISOString(),
                total_events: filteredEvents.length,
                events: filteredEvents.slice(0, 50)
            };
            
            const blob = new Blob([JSON.stringify(reportData, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `earthquake-report-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>'''

def main():
    port = 8517
    
    print("🎯 NEXUS Clean UI - Professional Earthquake Monitor")
    print("=" * 55)
    print("🎨 CLEAN DESIGN FEATURES:")
    print("  ✅ Minimalist white background")
    print("  ✅ Subtle shadows and borders")
    print("  ✅ Clean typography (Inter font)")
    print("  ✅ Muted color palette")
    print("  ✅ Reduced visual noise")
    print("  ✅ Professional button styles")
    print("  ✅ Simplified animations")
    print("  ✅ Better spacing and layout")
    print("=" * 55)
    print(f"🌐 Dashboard URL: http://localhost:{port}")
    print("📊 Real-time USGS earthquake data")
    print("🎯 Professional, clean interface")
    print("📱 Fully responsive design")
    print("=" * 55)
    print("✅ Clean UI ready for deployment!")
    print("=" * 55)
    
    try:
        with socketserver.TCPServer(("", port), CleanHTTPHandler) as httpd:
            print(f"✅ Server running at http://localhost:{port}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
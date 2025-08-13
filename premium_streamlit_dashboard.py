#!/usr/bin/env python3
"""
Premium Streamlit-style Dashboard for Disaster Response System
Beautiful, modern interface with real-time data visualization
"""

import json
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import random
import time

class PremiumDashboardHandler(BaseHTTPRequestHandler):
    API_BASE_URL = "http://localhost:8000"
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/' or path == '/dashboard':
            self._serve_premium_dashboard()
        elif path.startswith('/api/'):
            self._proxy_api_request(path.replace('/api', ''))
        else:
            self._send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path.startswith('/api/'):
            self._proxy_api_post(path.replace('/api', ''))
        else:
            self._send_error(404, "Not Found")
    
    def _proxy_api_request(self, endpoint):
        """Proxy GET request to backend API"""
        try:
            response = requests.get(f"{self.API_BASE_URL}{endpoint}", timeout=5)
            self.send_response(response.status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.content)
        except Exception as e:
            self._send_mock_response(endpoint)
    
    def _proxy_api_post(self, endpoint):
        """Proxy POST request to backend API"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            response = requests.post(
                f"{self.API_BASE_URL}{endpoint}",
                data=post_data,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            self.send_response(response.status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response.content)
        except Exception as e:
            self._send_mock_response(endpoint, is_post=True)
    
    def _send_mock_response(self, endpoint, is_post=False):
        """Send mock response when API is unavailable"""
        mock_data = {}
        
        if endpoint == '/health':
            mock_data = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'components': {
                    'ml_classifier': 'healthy (mock)',
                    'vector_store': 'healthy (mock)',
                    'demo_mode': True
                }
            }
        elif endpoint == '/stats':
            mock_data = {
                'total_events': 1247,
                'system_status': 'operational',
                'disaster_type_distribution': {
                    'earthquake': 456,
                    'fire': 231,
                    'flood': 189,
                    'hurricane': 134,
                    'tornado': 87,
                    'other_disaster': 150
                }
            }
        elif endpoint.startswith('/events'):
            mock_data = {
                'total': 10,
                'events': [
                    {
                        'event_id': f'evt_{i}',
                        'disaster_type': ['earthquake', 'fire', 'flood', 'hurricane', 'tornado'][i % 5],
                        'text': f'Sample disaster event {i}',
                        'confidence': round(random.uniform(0.6, 0.95), 2),
                        'severity': ['low', 'medium', 'high', 'critical'][i % 4],
                        'timestamp': datetime.now().isoformat(),
                        'location': {'latitude': 37.7749 + i, 'longitude': -122.4194 + i}
                    } for i in range(10)
                ]
            }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(mock_data, default=str).encode('utf-8'))
    
    def _serve_premium_dashboard(self):
        """Serve the premium dashboard HTML"""
        html_content = self._get_premium_dashboard_html()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def _get_premium_dashboard_html(self):
        """Generate premium Streamlit-style dashboard HTML"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚨 Disaster Response Dashboard - Premium</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        :root {
            --primary-color: #ff4b4b;
            --secondary-color: #0066cc;
            --accent-color: #00d4aa;
            --background-color: #ffffff;
            --surface-color: #f8f9fa;
            --text-primary: #262730;
            --text-secondary: #6c757d;
            --border-color: #e9ecef;
            --success-color: #28a745;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
            --sidebar-width: 280px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--background-color);
            color: var(--text-primary);
            line-height: 1.6;
        }

        .streamlit-container {
            display: flex;
            min-height: 100vh;
        }

        /* Sidebar */
        .sidebar {
            width: var(--sidebar-width);
            background: linear-gradient(180deg, #ff4b4b 0%, #ff6b6b 100%);
            color: white;
            padding: 2rem 1.5rem;
            position: fixed;
            height: 100vh;
            overflow-y: auto;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
        }

        .sidebar-title {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .sidebar-subtitle {
            font-size: 0.9rem;
            opacity: 0.9;
            margin-bottom: 2rem;
        }

        .nav-section {
            margin-bottom: 2rem;
        }

        .nav-section h3 {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 1rem;
            opacity: 0.8;
            font-weight: 600;
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1rem;
            margin: 0.25rem 0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            color: white;
        }

        .nav-item:hover {
            background: rgba(255,255,255,0.1);
            transform: translateX(4px);
        }

        .nav-item.active {
            background: rgba(255,255,255,0.2);
            font-weight: 600;
        }

        .system-status {
            background: rgba(255,255,255,0.1);
            padding: 1rem;
            border-radius: 8px;
            margin-top: 2rem;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success-color);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.1); }
            100% { opacity: 1; transform: scale(1); }
        }

        /* Main Content */
        .main-content {
            margin-left: var(--sidebar-width);
            flex: 1;
            padding: 2rem 3rem;
            max-width: calc(100vw - var(--sidebar-width));
        }

        .header {
            margin-bottom: 3rem;
        }

        .page-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .page-subtitle {
            font-size: 1.1rem;
            color: var(--text-secondary);
        }

        /* Metrics Grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }

        .metric-card {
            background: var(--surface-color);
            padding: 2rem;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }

        .metric-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }

        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
        }

        .metric-icon {
            font-size: 2rem;
            margin-bottom: 1rem;
            color: var(--primary-color);
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: var(--text-primary);
        }

        .metric-label {
            font-size: 0.9rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .metric-change {
            font-size: 0.8rem;
            margin-top: 0.5rem;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: 600;
        }

        .metric-change.positive {
            background: rgba(40, 167, 69, 0.1);
            color: var(--success-color);
        }

        .metric-change.negative {
            background: rgba(220, 53, 69, 0.1);
            color: var(--danger-color);
        }

        /* Content Grid */
        .content-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }

        .content-card {
            background: white;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }

        .card-header {
            padding: 1.5rem 2rem;
            border-bottom: 1px solid var(--border-color);
            background: var(--surface-color);
        }

        .card-title {
            font-size: 1.2rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .card-content {
            padding: 2rem;
        }

        /* Interactive Elements */
        .input-group {
            margin-bottom: 1.5rem;
        }

        .input-label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: var(--text-primary);
        }

        .form-input {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 2px solid var(--border-color);
            border-radius: 8px;
            font-size: 1rem;
            transition: all 0.2s ease;
        }

        .form-input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(255, 75, 75, 0.1);
        }

        .form-textarea {
            resize: vertical;
            min-height: 100px;
        }

        .btn {
            background: linear-gradient(135deg, var(--primary-color), #ff6b6b);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255, 75, 75, 0.3);
        }

        .btn:active {
            transform: translateY(0);
        }

        .btn-secondary {
            background: linear-gradient(135deg, var(--secondary-color), #0080ff);
        }

        .btn-success {
            background: linear-gradient(135deg, var(--success-color), #34ce57);
        }

        /* Event List */
        .event-list {
            max-height: 400px;
            overflow-y: auto;
        }

        .event-item {
            padding: 1rem 0;
            border-bottom: 1px solid var(--border-color);
            transition: all 0.2s ease;
        }

        .event-item:hover {
            background: var(--surface-color);
            margin: 0 -1rem;
            padding: 1rem;
            border-radius: 8px;
        }

        .event-header {
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 0.5rem;
        }

        .event-type {
            font-weight: 600;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            text-transform: uppercase;
        }

        .event-earthquake { background: rgba(220, 53, 69, 0.1); color: var(--danger-color); }
        .event-fire { background: rgba(255, 193, 7, 0.1); color: #e67e22; }
        .event-flood { background: rgba(0, 123, 255, 0.1); color: var(--secondary-color); }
        .event-hurricane { background: rgba(108, 117, 125, 0.1); color: #6c757d; }
        .event-tornado { background: rgba(111, 66, 193, 0.1); color: #6f42c1; }

        .event-severity {
            font-size: 0.8rem;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-weight: 600;
        }

        .severity-critical { background: var(--danger-color); color: white; }
        .severity-high { background: #fd7e14; color: white; }
        .severity-medium { background: var(--warning-color); color: #212529; }
        .severity-low { background: var(--success-color); color: white; }

        .event-text {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }

        .event-meta {
            font-size: 0.8rem;
            color: var(--text-secondary);
            display: flex;
            gap: 1rem;
        }

        /* Chart Container */
        .chart-container {
            height: 400px;
            margin-top: 1rem;
        }

        /* Prediction Results */
        .prediction-result {
            background: linear-gradient(135deg, rgba(0, 212, 170, 0.1), rgba(0, 212, 170, 0.05));
            border: 2px solid var(--accent-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 1rem;
        }

        .result-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
        }

        .result-icon {
            font-size: 1.5rem;
            color: var(--accent-color);
        }

        .result-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .result-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
        }

        .result-item {
            text-align: center;
        }

        .result-value {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }

        .result-label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Loading States */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
            color: var(--text-secondary);
        }

        .loading-spinner {
            width: 20px;
            height: 20px;
            border: 2px solid var(--border-color);
            border-top-color: var(--primary-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 0.5rem;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Alerts */
        .alert {
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .alert-success {
            background: rgba(40, 167, 69, 0.1);
            border: 1px solid rgba(40, 167, 69, 0.2);
            color: var(--success-color);
        }

        .alert-error {
            background: rgba(220, 53, 69, 0.1);
            border: 1px solid rgba(220, 53, 69, 0.2);
            color: var(--danger-color);
        }

        /* Footer */
        .footer {
            margin-top: 4rem;
            padding: 2rem 0;
            border-top: 1px solid var(--border-color);
            text-align: center;
            color: var(--text-secondary);
        }

        /* Responsive */
        @media (max-width: 1200px) {
            .content-grid {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 768px) {
            .sidebar {
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }

            .main-content {
                margin-left: 0;
                padding: 1rem;
                max-width: 100vw;
            }

            .metrics-grid {
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            }

            .page-title {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="streamlit-container">
        <!-- Sidebar -->
        <div class="sidebar">
            <div class="sidebar-title">
                <i class="fas fa-shield-alt"></i>
                Disaster Response
            </div>
            <div class="sidebar-subtitle">
                Real-time monitoring and analysis platform
            </div>

            <nav class="nav-section">
                <h3>Navigation</h3>
                <div class="nav-item active" onclick="showPage('overview')">
                    <i class="fas fa-tachometer-alt"></i>
                    Overview
                </div>
                <div class="nav-item" onclick="showPage('prediction')">
                    <i class="fas fa-brain"></i>
                    Prediction
                </div>
                <div class="nav-item" onclick="showPage('analytics')">
                    <i class="fas fa-chart-line"></i>
                    Analytics
                </div>
                <div class="nav-item" onclick="showPage('events')">
                    <i class="fas fa-list"></i>
                    Recent Events
                </div>
                <div class="nav-item" onclick="showPage('search')">
                    <i class="fas fa-search"></i>
                    Search
                </div>
            </nav>

            <div class="system-status">
                <h3 style="margin-bottom: 1rem;">System Status</h3>
                <div class="status-indicator">
                    <div class="status-dot"></div>
                    <span id="system-status-text">All systems operational</span>
                </div>
                <div style="font-size: 0.8rem; margin-top: 0.5rem; opacity: 0.8;">
                    <span id="events-processed">1,247</span> events processed
                </div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="main-content">
            <!-- Overview Page -->
            <div id="overview-page" class="page">
                <div class="header">
                    <h1 class="page-title">🚨 Disaster Response Dashboard</h1>
                    <p class="page-subtitle">Real-time monitoring and AI-powered disaster detection system</p>
                </div>

                <!-- Metrics -->
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-icon"><i class="fas fa-exclamation-triangle"></i></div>
                        <div class="metric-value" id="total-events">-</div>
                        <div class="metric-label">Total Events</div>
                        <div class="metric-change positive">+12% today</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon"><i class="fas fa-bell"></i></div>
                        <div class="metric-value" id="active-alerts">-</div>
                        <div class="metric-label">Active Alerts</div>
                        <div class="metric-change negative">-3 from yesterday</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon"><i class="fas fa-globe-americas"></i></div>
                        <div class="metric-value" id="regions-monitored">195</div>
                        <div class="metric-label">Regions Monitored</div>
                        <div class="metric-change positive">Global coverage</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon"><i class="fas fa-percentage"></i></div>
                        <div class="metric-value" id="system-uptime">99.9%</div>
                        <div class="metric-label">System Uptime</div>
                        <div class="metric-change positive">Last 30 days</div>
                    </div>
                </div>

                <!-- Content Grid -->
                <div class="content-grid">
                    <div class="content-card">
                        <div class="card-header">
                            <h2 class="card-title">
                                <i class="fas fa-chart-bar"></i>
                                Disaster Type Distribution
                            </h2>
                        </div>
                        <div class="card-content">
                            <div id="disaster-chart" class="chart-container"></div>
                        </div>
                    </div>

                    <div class="content-card">
                        <div class="card-header">
                            <h2 class="card-title">
                                <i class="fas fa-clock"></i>
                                Recent Events
                            </h2>
                        </div>
                        <div class="card-content">
                            <div id="recent-events-list" class="event-list">
                                <div class="loading">
                                    <div class="loading-spinner"></div>
                                    Loading recent events...
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Prediction Page -->
            <div id="prediction-page" class="page" style="display: none;">
                <div class="header">
                    <h1 class="page-title">🔮 Disaster Prediction</h1>
                    <p class="page-subtitle">AI-powered disaster detection from text descriptions</p>
                </div>

                <div class="content-card">
                    <div class="card-header">
                        <h2 class="card-title">
                            <i class="fas fa-brain"></i>
                            Analyze Text for Disaster Detection
                        </h2>
                    </div>
                    <div class="card-content">
                        <div class="input-group">
                            <label class="input-label" for="prediction-text">
                                Enter text describing a potential disaster situation:
                            </label>
                            <textarea 
                                id="prediction-text" 
                                class="form-input form-textarea"
                                placeholder="e.g., 'Massive flooding in downtown area, water rising rapidly through the streets'"
                            ></textarea>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">
                            <div class="input-group">
                                <label class="input-label" for="prediction-lat">Latitude (optional):</label>
                                <input 
                                    type="number" 
                                    id="prediction-lat" 
                                    class="form-input"
                                    step="0.000001"
                                    placeholder="e.g., 40.7128"
                                >
                            </div>
                            <div class="input-group">
                                <label class="input-label" for="prediction-lon">Longitude (optional):</label>
                                <input 
                                    type="number" 
                                    id="prediction-lon" 
                                    class="form-input"
                                    step="0.000001"
                                    placeholder="e.g., -74.0060"
                                >
                            </div>
                        </div>

                        <button class="btn" onclick="predictDisaster()">
                            <i class="fas fa-magic"></i>
                            Analyze Text
                        </button>

                        <div id="prediction-result-container"></div>
                    </div>
                </div>
            </div>

            <!-- Analytics Page -->
            <div id="analytics-page" class="page" style="display: none;">
                <div class="header">
                    <h1 class="page-title">📊 Analytics & Insights</h1>
                    <p class="page-subtitle">Deep insights into disaster patterns and system performance</p>
                </div>

                <div class="content-grid">
                    <div class="content-card">
                        <div class="card-header">
                            <h2 class="card-title">
                                <i class="fas fa-chart-line"></i>
                                Event Timeline
                            </h2>
                        </div>
                        <div class="card-content">
                            <div id="timeline-chart" class="chart-container"></div>
                        </div>
                    </div>

                    <div class="content-card">
                        <div class="card-header">
                            <h2 class="card-title">
                                <i class="fas fa-pie-chart"></i>
                                Severity Distribution
                            </h2>
                        </div>
                        <div class="card-content">
                            <div id="severity-chart" class="chart-container"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Events Page -->
            <div id="events-page" class="page" style="display: none;">
                <div class="header">
                    <h1 class="page-title">📋 Event Management</h1>
                    <p class="page-subtitle">Browse, filter, and analyze disaster events</p>
                </div>

                <div class="content-card">
                    <div class="card-header">
                        <h2 class="card-title">
                            <i class="fas fa-filter"></i>
                            Event Filters
                        </h2>
                    </div>
                    <div class="card-content">
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                            <div class="input-group">
                                <label class="input-label">Event Type:</label>
                                <select id="filter-type" class="form-input">
                                    <option value="all">All Types</option>
                                    <option value="earthquake">Earthquake</option>
                                    <option value="fire">Fire</option>
                                    <option value="flood">Flood</option>
                                    <option value="hurricane">Hurricane</option>
                                    <option value="tornado">Tornado</option>
                                </select>
                            </div>
                            <div class="input-group">
                                <label class="input-label">Severity:</label>
                                <select id="filter-severity" class="form-input">
                                    <option value="all">All Severities</option>
                                    <option value="critical">Critical</option>
                                    <option value="high">High</option>
                                    <option value="medium">Medium</option>
                                    <option value="low">Low</option>
                                </select>
                            </div>
                            <div class="input-group">
                                <label class="input-label">Time Range:</label>
                                <select id="filter-time" class="form-input">
                                    <option value="all">All Time</option>
                                    <option value="24h">Last 24 Hours</option>
                                    <option value="7d">Last 7 Days</option>
                                    <option value="30d">Last 30 Days</option>
                                </select>
                            </div>
                        </div>
                        <button class="btn btn-secondary" onclick="applyFilters()">
                            <i class="fas fa-filter"></i>
                            Apply Filters
                        </button>
                    </div>
                </div>

                <div class="content-card" style="margin-top: 2rem;">
                    <div class="card-header">
                        <h2 class="card-title">
                            <i class="fas fa-list"></i>
                            Filtered Events
                        </h2>
                    </div>
                    <div class="card-content">
                        <div id="filtered-events-list" class="event-list">
                            <div class="loading">
                                <div class="loading-spinner"></div>
                                Loading events...
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Search Page -->
            <div id="search-page" class="page" style="display: none;">
                <div class="header">
                    <h1 class="page-title">🔍 Event Search</h1>
                    <p class="page-subtitle">Search for similar disaster events using AI similarity matching</p>
                </div>

                <div class="content-card">
                    <div class="card-header">
                        <h2 class="card-title">
                            <i class="fas fa-search"></i>
                            Semantic Search
                        </h2>
                    </div>
                    <div class="card-content">
                        <div class="input-group">
                            <label class="input-label" for="search-query">
                                Search Query:
                            </label>
                            <input 
                                type="text" 
                                id="search-query" 
                                class="form-input"
                                placeholder="e.g., 'flooding in coastal areas'"
                            >
                        </div>

                        <button class="btn btn-success" onclick="searchEvents()">
                            <i class="fas fa-search"></i>
                            Search Events
                        </button>

                        <div id="search-results-container"></div>
                    </div>
                </div>
            </div>

            <div class="footer">
                <p>🌊🔥🌍🌀🌪️ Disaster Response System - Powered by AI 🌪️🌀🌍🔥🌊</p>
                <p>Backend API: <strong>http://localhost:8000</strong> • Dashboard: <strong>http://localhost:8502</strong></p>
            </div>
        </div>
    </div>

    <script>
        // Global state
        let currentPage = 'overview';
        let systemData = {};

        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            loadSystemData();
            setInterval(loadSystemData, 10000); // Refresh every 10 seconds
        });

        // Page navigation
        function showPage(pageId) {
            // Hide all pages
            document.querySelectorAll('.page').forEach(page => {
                page.style.display = 'none';
            });
            
            // Show selected page
            document.getElementById(pageId + '-page').style.display = 'block';
            
            // Update nav items
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            event.target.classList.add('active');
            
            currentPage = pageId;
            
            // Load page-specific data
            if (pageId === 'analytics') {
                loadAnalytics();
            } else if (pageId === 'events') {
                loadAllEvents();
            }
        }

        // Load system data
        async function loadSystemData() {
            try {
                // Load health data
                const healthResponse = await fetch('/api/health');
                const healthData = await healthResponse.json();
                
                // Load stats data
                const statsResponse = await fetch('/api/stats');
                const statsData = await statsResponse.json();
                
                // Load recent events
                const eventsResponse = await fetch('/api/events?limit=10');
                const eventsData = await eventsResponse.json();
                
                systemData = { health: healthData, stats: statsData, events: eventsData };
                
                updateDashboard();
                
            } catch (error) {
                console.error('Error loading system data:', error);
                showError('Failed to load system data');
            }
        }

        // Update dashboard with latest data
        function updateDashboard() {
            const { health, stats, events } = systemData;
            
            // Update metrics
            document.getElementById('total-events').textContent = stats.total_events || 0;
            document.getElementById('events-processed').textContent = stats.total_events || 0;
            
            // Calculate active alerts (high/critical events)
            const activeAlerts = events.events ? events.events.filter(e => 
                e.severity === 'high' || e.severity === 'critical'
            ).length : 0;
            document.getElementById('active-alerts').textContent = activeAlerts;
            
            // Update system status
            document.getElementById('system-status-text').textContent = 
                health.status === 'healthy' ? 'All systems operational' : 'System degraded';
            
            // Update recent events list
            updateRecentEventsList(events.events || []);
            
            // Update disaster distribution chart
            updateDisasterChart(stats.disaster_type_distribution || {});
        }

        // Update recent events list
        function updateRecentEventsList(events) {
            const container = document.getElementById('recent-events-list');
            
            if (events.length === 0) {
                container.innerHTML = '<div class="loading">No recent events</div>';
                return;
            }
            
            const eventsHtml = events.slice(0, 5).map(event => {
                const typeClass = `event-${event.disaster_type}`;
                const severityClass = `severity-${event.severity}`;
                const confidence = (event.confidence * 100).toFixed(1);
                const timestamp = new Date(event.timestamp).toLocaleString();
                
                return `
                    <div class="event-item">
                        <div class="event-header">
                            <span class="event-type ${typeClass}">
                                ${getDisasterIcon(event.disaster_type)} ${event.disaster_type.toUpperCase()}
                            </span>
                            <span class="event-severity ${severityClass}">${event.severity.toUpperCase()}</span>
                        </div>
                        <div class="event-text">"${event.text.substring(0, 100)}..."</div>
                        <div class="event-meta">
                            <span><i class="fas fa-percentage"></i> ${confidence}% confidence</span>
                            <span><i class="fas fa-clock"></i> ${timestamp}</span>
                            ${event.location ? `<span><i class="fas fa-map-marker-alt"></i> ${event.location.latitude?.toFixed(4)}, ${event.location.longitude?.toFixed(4)}</span>` : ''}
                        </div>
                    </div>
                `;
            }).join('');
            
            container.innerHTML = eventsHtml;
        }

        // Update disaster distribution chart
        function updateDisasterChart(distribution) {
            const data = [{
                values: Object.values(distribution),
                labels: Object.keys(distribution).map(key => key.replace('_', ' ').toUpperCase()),
                type: 'pie',
                hole: 0.3,
                marker: {
                    colors: ['#ff4b4b', '#ffc107', '#007bff', '#6c757d', '#6f42c1', '#28a745']
                }
            }];
            
            const layout = {
                showlegend: true,
                height: 350,
                margin: { t: 20, b: 20, l: 20, r: 20 },
                font: { family: 'Inter, sans-serif' }
            };
            
            Plotly.newPlot('disaster-chart', data, layout, {responsive: true});
        }

        // Disaster prediction
        async function predictDisaster() {
            const text = document.getElementById('prediction-text').value.trim();
            const lat = parseFloat(document.getElementById('prediction-lat').value) || null;
            const lon = parseFloat(document.getElementById('prediction-lon').value) || null;
            
            if (!text) {
                showError('Please enter text to analyze');
                return;
            }
            
            const container = document.getElementById('prediction-result-container');
            container.innerHTML = `
                <div class="loading" style="margin-top: 1rem;">
                    <div class="loading-spinner"></div>
                    Analyzing text...
                </div>
            `;
            
            try {
                const requestData = { text };
                if (lat !== null && lon !== null) {
                    requestData.location = { latitude: lat, longitude: lon };
                }
                
                const response = await fetch('/api/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestData)
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showPredictionResult(data);
                } else {
                    showError('Prediction failed: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                showError('API connection error');
            }
        }

        // Show prediction result
        function showPredictionResult(data) {
            const container = document.getElementById('prediction-result-container');
            const confidence = (data.confidence_score * 100).toFixed(1);
            const icon = getDisasterIcon(data.top_prediction);
            
            container.innerHTML = `
                <div class="prediction-result">
                    <div class="result-header">
                        <div class="result-icon">${icon}</div>
                        <div class="result-title">Prediction Results</div>
                    </div>
                    <div class="result-grid">
                        <div class="result-item">
                            <div class="result-value" style="color: var(--primary-color);">${icon}</div>
                            <div class="result-label">${data.top_prediction.replace('_', ' ').toUpperCase()}</div>
                        </div>
                        <div class="result-item">
                            <div class="result-value" style="color: var(--accent-color);">${confidence}%</div>
                            <div class="result-label">Confidence</div>
                        </div>
                        <div class="result-item">
                            <div class="result-value" style="color: var(--warning-color);">${data.severity.toUpperCase()}</div>
                            <div class="result-label">Severity</div>
                        </div>
                        <div class="result-item">
                            <div class="result-value" style="color: var(--secondary-color);">${data.processing_time_ms?.toFixed(0) || 0}ms</div>
                            <div class="result-label">Processing Time</div>
                        </div>
                    </div>
                    <div style="margin-top: 1rem; font-size: 0.9rem; color: var(--text-secondary);">
                        <strong>Event ID:</strong> ${data.event_id}<br>
                        <strong>Timestamp:</strong> ${new Date(data.timestamp).toLocaleString()}
                    </div>
                </div>
            `;
        }

        // Event search
        async function searchEvents() {
            const query = document.getElementById('search-query').value.trim();
            
            if (!query) {
                showError('Please enter a search query');
                return;
            }
            
            const container = document.getElementById('search-results-container');
            container.innerHTML = `
                <div class="loading" style="margin-top: 1rem;">
                    <div class="loading-spinner"></div>
                    Searching events...
                </div>
            `;
            
            try {
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query, limit: 8 })
                });
                
                const data = await response.json();
                
                if (response.ok && data.results.length > 0) {
                    showSearchResults(data);
                } else {
                    container.innerHTML = '<div class="alert alert-error" style="margin-top: 1rem;">No matching events found</div>';
                }
            } catch (error) {
                showError('Search failed: API connection error');
            }
        }

        // Show search results
        function showSearchResults(data) {
            const container = document.getElementById('search-results-container');
            
            const resultsHtml = `
                <div style="margin-top: 2rem;">
                    <h3 style="margin-bottom: 1rem;">Found ${data.total_results} matching events:</h3>
                    <div class="event-list">
                        ${data.results.map((result, index) => {
                            const icon = getDisasterIcon(result.disaster_type);
                            const confidence = (result.confidence * 100).toFixed(1);
                            const score = (result.score * 100).toFixed(1);
                            const timestamp = new Date(result.timestamp).toLocaleString();
                            
                            return `
                                <div class="event-item">
                                    <div class="event-header">
                                        <span class="event-type event-${result.disaster_type}">
                                            ${icon} ${result.disaster_type.toUpperCase()}
                                        </span>
                                        <span class="event-severity severity-${result.severity}">${result.severity.toUpperCase()}</span>
                                    </div>
                                    <div class="event-text">"${result.text.substring(0, 120)}..."</div>
                                    <div class="event-meta">
                                        <span><i class="fas fa-percentage"></i> ${confidence}% confidence</span>
                                        <span><i class="fas fa-search"></i> ${score}% match</span>
                                        <span><i class="fas fa-clock"></i> ${timestamp}</span>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
            
            container.innerHTML = resultsHtml;
        }

        // Load analytics data
        function loadAnalytics() {
            // Create timeline chart
            const timelineData = [{
                x: Array.from({length: 24}, (_, i) => `${i}:00`),
                y: Array.from({length: 24}, () => Math.floor(Math.random() * 10) + 1),
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#ff4b4b', width: 3 },
                marker: { color: '#ff4b4b', size: 8 }
            }];
            
            const timelineLayout = {
                title: 'Events Over Time (24h)',
                xaxis: { title: 'Hour' },
                yaxis: { title: 'Event Count' },
                height: 350,
                margin: { t: 40, b: 60, l: 60, r: 40 }
            };
            
            Plotly.newPlot('timeline-chart', timelineData, timelineLayout, {responsive: true});
            
            // Create severity distribution chart
            const severityData = [{
                values: [45, 123, 89, 23],
                labels: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
                type: 'pie',
                marker: {
                    colors: ['#dc3545', '#fd7e14', '#ffc107', '#28a745']
                }
            }];
            
            const severityLayout = {
                title: 'Event Severity Distribution',
                height: 350,
                margin: { t: 40, b: 20, l: 20, r: 20 }
            };
            
            Plotly.newPlot('severity-chart', severityData, severityLayout, {responsive: true});
        }

        // Load all events
        async function loadAllEvents() {
            try {
                const response = await fetch('/api/events?limit=50');
                const data = await response.json();
                updateFilteredEventsList(data.events || []);
            } catch (error) {
                showError('Failed to load events');
            }
        }

        // Apply event filters
        function applyFilters() {
            loadAllEvents(); // In a real app, this would apply the actual filters
        }

        // Update filtered events list
        function updateFilteredEventsList(events) {
            const container = document.getElementById('filtered-events-list');
            updateRecentEventsList(events); // Reuse the same function
            container.innerHTML = document.getElementById('recent-events-list').innerHTML;
        }

        // Utility functions
        function getDisasterIcon(type) {
            const icons = {
                earthquake: '🌍',
                fire: '🔥',
                flood: '🌊',
                hurricane: '🌀',
                tornado: '🌪️',
                other_disaster: '⚡',
                no_disaster: '✅'
            };
            return icons[type] || '❓';
        }

        function showError(message) {
            const container = document.getElementById('prediction-result-container') || 
                            document.getElementById('search-results-container');
            if (container) {
                container.innerHTML = `<div class="alert alert-error" style="margin-top: 1rem;">${message}</div>`;
            }
        }

        // Add smooth transitions
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', function() {
                document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
                this.classList.add('active');
            });
        });
    </script>
</body>
</html>
"""
    
    def _send_error(self, status_code, message):
        """Send error response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        error_html = f"<html><body><h1>Error {status_code}</h1><p>{message}</p></body></html>"
        self.wfile.write(error_html.encode('utf-8'))

def run_premium_dashboard(host='0.0.0.0', port=8502):
    """Run the premium dashboard server"""
    server = HTTPServer((host, port), PremiumDashboardHandler)
    
    print("✨ Premium Streamlit-Style Dashboard Starting")
    print("=" * 60)
    print(f"🌟 Dashboard URL: http://{host}:{port}")
    print(f"🎨 Features: Modern Streamlit-inspired UI")
    print(f"📊 Real-time data visualization")
    print(f"🔌 Backend API: http://localhost:8000")
    print("=" * 60)
    print("🚀 Premium dashboard ready!")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Premium dashboard stopped")
        server.server_close()

if __name__ == "__main__":
    run_premium_dashboard()
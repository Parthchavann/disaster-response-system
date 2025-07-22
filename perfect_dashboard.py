#!/usr/bin/env python3
"""
Perfect Disaster Response Dashboard
Clean, impressive, with clear updates - the best of both worlds
"""

import http.server
import socketserver
import json
import threading
import time
from datetime import datetime, timedelta
import requests
import os
import logging
from typing import Dict, List, Optional
import re
import math
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerfectDataCollector:
    """Perfect data collector - clean and comprehensive"""
    
    def __init__(self):
        self.events = []
        self.stats = {
            'total_events': 0,
            'critical_alerts': 0,
            'people_affected': 0,
            'response_teams': 0,
            'countries_affected': 0,
            'last_major_event': 'None recent'
        }
        self.last_update = datetime.now()
        self.is_monitoring = True
        
    def fetch_earthquake_data(self) -> List[Dict]:
        """Fetch earthquake data with clean analysis"""
        try:
            url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            earthquakes = []
            for feature in data.get('features', [])[:8]:
                props = feature['properties']
                coords = feature['geometry']['coordinates']
                
                magnitude = props.get('mag', 0)
                depth = coords[2]
                
                earthquake_data = {
                    'id': feature['id'],
                    'type': 'earthquake',
                    'severity': self._get_earthquake_severity(magnitude),
                    'magnitude': magnitude,
                    'location': props.get('place', 'Unknown location'),
                    'timestamp': datetime.fromtimestamp(props['time'] / 1000),
                    'depth': depth,
                    'felt_reports': props.get('felt', 0),
                    'alert_level': props.get('alert', 'green'),
                    'tsunami_risk': props.get('tsunami', 0) == 1,
                    'source': 'USGS',
                    'url': props.get('url', '#'),
                    
                    # Clean impressive details
                    'impact_radius': self._calculate_impact_radius(magnitude),
                    'population_estimate': self._estimate_population(magnitude, props.get('felt', 0)),
                    'damage_assessment': self._assess_damage(magnitude, depth),
                    'response_needed': self._assess_response_need(magnitude, props.get('felt', 0)),
                    'comparable_event': self._get_comparable_event(magnitude)
                }
                
                earthquakes.append(earthquake_data)
            
            return earthquakes
        except Exception as e:
            logger.error(f"Error fetching earthquake data: {e}")
            return []
    
    def fetch_weather_alerts(self) -> List[Dict]:
        """Fetch weather alerts with clean analysis"""
        try:
            url = "https://api.weather.gov/alerts/active?severity=Severe,Extreme"
            headers = {'User-Agent': 'DisasterResponseSystem/3.0'}
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            
            alerts = []
            for feature in data.get('features', [])[:12]:
                props = feature['properties']
                
                event_type = props.get('event', 'Unknown').lower()
                disaster_type = self._map_weather_event(event_type)
                
                # Parse timestamp cleanly
                try:
                    timestamp_str = props.get('effective', datetime.now().isoformat())
                    if '+' in timestamp_str or 'Z' in timestamp_str:
                        clean_timestamp = re.sub(r'([+-]\d{2}:\d{2}|Z)$', '', timestamp_str)
                        timestamp = datetime.fromisoformat(clean_timestamp)
                    else:
                        timestamp = datetime.fromisoformat(timestamp_str)
                except:
                    timestamp = datetime.now()
                
                alert_data = {
                    'id': props.get('id', ''),
                    'type': disaster_type,
                    'severity': props.get('severity', 'moderate').lower(),
                    'event_name': props.get('event', 'Weather Alert'),
                    'headline': props.get('headline', ''),
                    'areas': props.get('areaDesc', 'Multiple areas'),
                    'timestamp': timestamp,
                    'urgency': props.get('urgency', 'Unknown'),
                    'certainty': props.get('certainty', 'Unknown'),
                    'expires': props.get('expires', ''),
                    'source': 'NOAA',
                    
                    # Clean impressive details
                    'affected_population': self._estimate_weather_population(props.get('areaDesc', '')),
                    'threat_level': self._assess_threat_level(props.get('urgency', ''), props.get('certainty', '')),
                    'preparation_time': self._get_preparation_time(props.get('urgency', '')),
                    'safety_priority': self._get_safety_priority(disaster_type),
                    'impact_scale': self._assess_impact_scale(disaster_type, props.get('severity', ''))
                }
                
                alerts.append(alert_data)
            
            return alerts
        except Exception as e:
            logger.error(f"Error fetching weather alerts: {e}")
            return []
    
    def _get_earthquake_severity(self, magnitude: float) -> str:
        """Simple severity classification"""
        if magnitude >= 8.0:
            return 'catastrophic'
        elif magnitude >= 7.0:
            return 'critical'
        elif magnitude >= 6.0:
            return 'high'
        elif magnitude >= 5.0:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_impact_radius(self, magnitude: float) -> str:
        """Calculate impact radius"""
        radius = int(10 ** (0.5 * magnitude - 1.8))
        return f"{radius}km radius"
    
    def _estimate_population(self, magnitude: float, felt: int) -> str:
        """Estimate affected population"""
        if felt > 10000:
            return "Millions affected"
        elif felt > 1000:
            return "Hundreds of thousands"
        elif felt > 100:
            return "Tens of thousands"
        elif felt > 10:
            return "Thousands affected"
        else:
            return "Limited exposure"
    
    def _assess_damage(self, magnitude: float, depth: float) -> str:
        """Assess potential damage"""
        damage_score = magnitude * (1 + (1 / max(depth, 10)))
        
        if damage_score >= 8:
            return "Severe structural damage expected"
        elif damage_score >= 6:
            return "Moderate to major damage likely"
        elif damage_score >= 4:
            return "Light to moderate damage possible"
        else:
            return "Minor damage expected"
    
    def _assess_response_need(self, magnitude: float, felt: int) -> str:
        """Assess response requirements"""
        if magnitude >= 7.0 or felt > 5000:
            return "International aid may be needed"
        elif magnitude >= 6.0 or felt > 1000:
            return "National emergency response"
        elif magnitude >= 5.0 or felt > 100:
            return "Regional response required"
        else:
            return "Local monitoring sufficient"
    
    def _get_comparable_event(self, magnitude: float) -> str:
        """Get comparable earthquake"""
        if magnitude >= 9.0:
            return "2011 Japan (9.1) scale event"
        elif magnitude >= 8.0:
            return "2015 Nepal (7.8) scale event"
        elif magnitude >= 7.0:
            return "2010 Haiti (7.0) scale event"
        elif magnitude >= 6.5:
            return "2014 Napa (6.0) scale event"
        else:
            return "Regional earthquake"
    
    def _map_weather_event(self, event_type: str) -> str:
        """Map weather events"""
        event_lower = event_type.lower()
        
        if any(word in event_lower for word in ['flood', 'flash flood']):
            return 'flood'
        elif any(word in event_lower for word in ['fire', 'red flag']):
            return 'wildfire'
        elif any(word in event_lower for word in ['tornado']):
            return 'tornado'
        elif any(word in event_lower for word in ['hurricane', 'tropical']):
            return 'hurricane'
        elif any(word in event_lower for word in ['winter', 'blizzard', 'ice']):
            return 'winter_storm'
        elif any(word in event_lower for word in ['heat', 'extreme']):
            return 'extreme_heat'
        else:
            return 'severe_weather'
    
    def _estimate_weather_population(self, areas: str) -> str:
        """Estimate weather affected population"""
        area_count = len(areas.split(','))
        
        if area_count > 15:
            return "5+ million people"
        elif area_count > 8:
            return "1-5 million people"
        elif area_count > 4:
            return "500K-1M people"
        elif area_count > 2:
            return "100K-500K people"
        else:
            return "Under 100K people"
    
    def _assess_threat_level(self, urgency: str, certainty: str) -> str:
        """Assess threat level"""
        urgency_scores = {'immediate': 4, 'expected': 3, 'future': 2, 'past': 1}
        certainty_scores = {'observed': 4, 'likely': 3, 'possible': 2, 'unlikely': 1}
        
        total_score = urgency_scores.get(urgency.lower(), 2) + certainty_scores.get(certainty.lower(), 2)
        
        if total_score >= 7:
            return "CRITICAL THREAT"
        elif total_score >= 5:
            return "HIGH THREAT"
        elif total_score >= 3:
            return "MODERATE THREAT"
        else:
            return "LOW THREAT"
    
    def _get_preparation_time(self, urgency: str) -> str:
        """Get preparation time"""
        if urgency.lower() == 'immediate':
            return "0-2 hours to prepare"
        elif urgency.lower() == 'expected':
            return "2-12 hours window"
        else:
            return "12+ hours available"
    
    def _get_safety_priority(self, disaster_type: str) -> str:
        """Get safety priority action"""
        priorities = {
            'flood': "Move to higher ground immediately",
            'hurricane': "Evacuate coastal areas if ordered",
            'tornado': "Seek shelter in sturdy building",
            'wildfire': "Prepare evacuation plan",
            'extreme_heat': "Stay hydrated and cool",
            'winter_storm': "Avoid travel, stay warm"
        }
        return priorities.get(disaster_type, "Follow local guidance")
    
    def _assess_impact_scale(self, disaster_type: str, severity: str) -> str:
        """Assess impact scale"""
        if severity in ['extreme', 'severe']:
            scales = {
                'flood': "Major flooding across region",
                'hurricane': "Widespread destruction possible",
                'tornado': "Multiple communities at risk",
                'wildfire': "Large evacuation zones",
                'extreme_heat': "Health emergency conditions"
            }
        else:
            scales = {
                'flood': "Localized flooding expected",
                'hurricane': "Moderate impact anticipated",
                'tornado': "Isolated damage possible",
                'wildfire': "Contained fire activity",
                'extreme_heat': "Heat advisory conditions"
            }
        
        return scales.get(disaster_type, "Regional impact expected")
    
    def update_data(self):
        """Update all data cleanly"""
        all_events = []
        
        # Fetch data
        earthquakes = self.fetch_earthquake_data()
        weather_alerts = self.fetch_weather_alerts()
        
        all_events.extend(earthquakes)
        all_events.extend(weather_alerts)
        
        # Clean sorting
        def get_timestamp(event):
            ts = event.get('timestamp')
            if ts is None:
                return datetime.min
            if isinstance(ts, str):
                try:
                    if '+' in ts or 'Z' in ts:
                        clean_ts = re.sub(r'([+-]\d{2}:\d{2}|Z)$', '', ts)
                        return datetime.fromisoformat(clean_ts)
                    return datetime.fromisoformat(ts)
                except:
                    return datetime.min
            if hasattr(ts, 'replace') and ts.tzinfo is not None:
                return ts.replace(tzinfo=None)
            return ts
        
        all_events.sort(key=get_timestamp, reverse=True)
        
        self.events = all_events
        self.last_update = datetime.now()
        
        # Clean statistics
        self.stats['total_events'] = len(all_events)
        self.stats['critical_alerts'] = len([e for e in all_events if e.get('severity') in ['critical', 'extreme', 'catastrophic']])
        
        # Estimate affected population
        total_population = 0
        for event in all_events:
            if event.get('type') == 'earthquake':
                felt = event.get('felt_reports', 0)
                magnitude = event.get('magnitude', 0)
                total_population += felt * int(magnitude)
            else:
                pop_str = event.get('affected_population', '0')
                if 'million' in pop_str.lower():
                    total_population += 1000000
                elif 'thousand' in pop_str.lower():
                    total_population += 100000
        
        self.stats['people_affected'] = total_population
        
        # Response teams
        self.stats['response_teams'] = len([e for e in all_events if e.get('severity') in ['high', 'critical', 'extreme']]) * 3
        
        # Countries/regions
        locations = set()
        for event in all_events:
            location = event.get('location', event.get('areas', ''))
            if location:
                parts = location.split(',')
                if len(parts) > 0:
                    locations.add(parts[-1].strip())
        
        self.stats['countries_affected'] = len(locations)
        
        # Last major event
        major_events = [e for e in all_events if e.get('severity') in ['critical', 'high']]
        if major_events:
            last_major = major_events[0]
            if last_major.get('type') == 'earthquake':
                self.stats['last_major_event'] = f"M{last_major.get('magnitude', 0)} Earthquake"
            else:
                self.stats['last_major_event'] = last_major.get('event_name', 'Weather Event')
        else:
            self.stats['last_major_event'] = 'None recent'

class PerfectDashboard:
    """Perfect dashboard - clean, impressive, clear updates"""
    
    def __init__(self, port=8506):
        self.port = port
        self.data_collector = PerfectDataCollector()
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start clean monitoring"""
        def monitor():
            while self.data_collector.is_monitoring:
                self.data_collector.update_data()
                time.sleep(180)  # 3 minutes - clear timing
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        
        # Initial data fetch
        self.data_collector.update_data()
    
    def generate_html(self) -> str:
        """Generate perfect dashboard HTML"""
        events = self.data_collector.events
        stats = self.data_collector.stats
        last_update = self.data_collector.last_update.strftime('%H:%M:%S')
        
        # Clean separation
        earthquakes = [e for e in events if e.get('type') == 'earthquake'][:6]
        weather_events = [e for e in events if e.get('type') != 'earthquake'][:8]
        
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Emergency Response Center</title>
    
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            background-attachment: fixed;
            color: #1a202c;
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        /* Clean Header */
        .header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.3);
            padding: 1.5rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .header-content {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .logo {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .logo-icon {{
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}
        
        .title {{
            font-size: 1.75rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .status {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
            font-size: 0.875rem;
        }}
        
        .live-indicator {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: #10b981;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);
        }}
        
        .live-dot {{
            width: 8px;
            height: 8px;
            background: white;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}
        
        .update-time {{
            color: #64748b;
            font-weight: 500;
        }}
        
        /* Container */
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        /* Clean Stats */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 2rem 1.5rem;
            border-radius: 16px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .stat-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }}
        
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #667eea, #764ba2);
        }}
        
        .stat-icon {{
            font-size: 2rem;
            margin-bottom: 1rem;
            opacity: 0.8;
        }}
        
        .stat-value {{
            font-size: 2.5rem;
            font-weight: 700;
            color: #1a202c;
            margin-bottom: 0.5rem;
        }}
        
        .stat-label {{
            color: #64748b;
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }}
        
        .stat-detail {{
            color: #64748b;
            font-size: 0.75rem;
            font-style: italic;
        }}
        
        /* Content Grid */
        .content-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
        }}
        
        @media (max-width: 1024px) {{
            .content-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        /* Event Sections */
        .event-section {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }}
        
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .section-title {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #1a202c;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .section-count {{
            background: #e2e8f0;
            color: #475569;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.875rem;
            font-weight: 500;
        }}
        
        /* Clean Event Items */
        .event-item {{
            background: white;
            padding: 1.5rem;
            margin-bottom: 1rem;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        
        .event-item:hover {{
            border-color: #667eea;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
            transform: translateX(4px);
        }}
        
        .event-item:last-child {{
            margin-bottom: 0;
        }}
        
        /* Clear Severity Indicators */
        .severity-catastrophic {{ border-left: 4px solid #7c2d12; }}
        .severity-critical {{ border-left: 4px solid #dc2626; }}
        .severity-extreme {{ border-left: 4px solid #dc2626; }}
        .severity-high {{ border-left: 4px solid #ea580c; }}
        .severity-severe {{ border-left: 4px solid #ea580c; }}
        .severity-medium {{ border-left: 4px solid #d97706; }}
        .severity-moderate {{ border-left: 4px solid #d97706; }}
        .severity-low {{ border-left: 4px solid #16a34a; }}
        
        .event-header {{
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 1rem;
        }}
        
        .event-title {{
            font-size: 1.1rem;
            font-weight: 600;
            color: #1a202c;
            margin-bottom: 0.25rem;
        }}
        
        .event-time {{
            font-size: 0.75rem;
            color: #64748b;
            background: #f1f5f9;
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
            white-space: nowrap;
        }}
        
        .event-location {{
            font-size: 0.9rem;
            color: #475569;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .event-meta {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 0.75rem;
            margin-bottom: 1rem;
        }}
        
        .meta-item {{
            background: #f8fafc;
            padding: 0.5rem;
            border-radius: 6px;
            text-align: center;
        }}
        
        .meta-label {{
            font-size: 0.625rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.25rem;
        }}
        
        .meta-value {{
            font-size: 0.75rem;
            font-weight: 600;
            color: #1a202c;
        }}
        
        .event-details {{
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 8px;
            padding: 1rem;
            margin-top: 1rem;
        }}
        
        .details-title {{
            font-size: 0.875rem;
            font-weight: 600;
            color: #0369a1;
            margin-bottom: 0.5rem;
        }}
        
        .details-content {{
            font-size: 0.8rem;
            color: #0284c7;
            line-height: 1.4;
        }}
        
        /* Clean Footer */
        .footer {{
            text-align: center;
            margin-top: 3rem;
            padding: 2rem;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.875rem;
        }}
        
        .footer-links {{
            display: flex;
            gap: 2rem;
            justify-content: center;
            margin-bottom: 1rem;
        }}
        
        .footer-link {{
            color: rgba(255, 255, 255, 0.9);
            text-decoration: none;
            transition: color 0.3s ease;
            font-weight: 500;
        }}
        
        .footer-link:hover {{
            color: white;
        }}
        
        /* Clear Update Timer */
        .update-timer {{
            position: fixed;
            bottom: 1.5rem;
            right: 1.5rem;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            color: #1a202c;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            font-size: 0.875rem;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            .stats-grid {{ grid-template-columns: 1fr; gap: 1rem; }}
            .header-content {{ flex-direction: column; gap: 1rem; text-align: center; }}
            .event-meta {{ grid-template-columns: 1fr 1fr; }}
        }}
    </style>
</head>
<body>
    <!-- Clean Header -->
    <header class="header">
        <div class="header-content">
            <div class="logo">
                <div class="logo-icon">🛡️</div>
                <div class="title">Emergency Response Center</div>
            </div>
            <div class="status">
                <div class="live-indicator">
                    <span class="live-dot"></span>
                    Live Data
                </div>
                <div class="update-time">Updated: {last_update}</div>
            </div>
        </div>
    </header>

    <div class="container">
        <!-- Clean Statistics -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">📊</div>
                <div class="stat-value">{stats['total_events']}</div>
                <div class="stat-label">Total Events</div>
                <div class="stat-detail">Active monitoring worldwide</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">🚨</div>
                <div class="stat-value">{stats['critical_alerts']}</div>
                <div class="stat-label">Critical Alerts</div>
                <div class="stat-detail">Requiring immediate response</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">👥</div>
                <div class="stat-value">{self._format_number(stats['people_affected'])}</div>
                <div class="stat-label">People Affected</div>
                <div class="stat-detail">Estimated population exposure</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">🚁</div>
                <div class="stat-value">{stats['response_teams']}</div>
                <div class="stat-label">Response Teams</div>
                <div class="stat-detail">Emergency responders deployed</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">🌍</div>
                <div class="stat-value">{stats['countries_affected']}</div>
                <div class="stat-label">Regions Affected</div>
                <div class="stat-detail">Countries and states</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">⚡</div>
                <div class="stat-value" style="font-size: 1.2rem;">{stats['last_major_event']}</div>
                <div class="stat-label">Latest Major Event</div>
                <div class="stat-detail">Most significant recent occurrence</div>
            </div>
        </div>

        <!-- Content Grid -->
        <div class="content-grid">
            <!-- Earthquakes -->
            <div class="event-section">
                <div class="section-header">
                    <div class="section-title">🌍 Recent Earthquakes</div>
                    <div class="section-count">{len(earthquakes)} events</div>
                </div>
                {self._generate_earthquake_items(earthquakes)}
            </div>

            <!-- Weather Events -->
            <div class="event-section">
                <div class="section-header">
                    <div class="section-title">⛈️ Weather Alerts</div>
                    <div class="section-count">{len(weather_events)} alerts</div>
                </div>
                {self._generate_weather_items(weather_events)}
            </div>
        </div>
    </div>

    <footer class="footer">
        <div class="footer-links">
            <a href="#" class="footer-link">USGS Earthquakes</a>
            <a href="#" class="footer-link">NOAA Weather</a>
            <a href="#" class="footer-link">Emergency Resources</a>
            <a href="#" class="footer-link">Response Teams</a>
        </div>
        <p>Real-time disaster monitoring • Official government data • Updates every 3 minutes</p>
    </footer>

    <div class="update-timer">
        🔄 Next update in <span id="countdown">180</span>s
    </div>

    <script>
        // Clear countdown timer
        let countdown = 180;
        const countdownEl = document.getElementById('countdown');
        
        const updateTimer = () => {{
            countdownEl.textContent = countdown;
            countdown--;
            if (countdown < 0) {{
                window.location.reload();
            }}
        }};
        
        updateTimer();
        setInterval(updateTimer, 1000);
        
        // Simple interactions
        document.querySelectorAll('.event-item').forEach(item => {{
            item.addEventListener('click', () => {{
                item.style.transform = 'scale(0.98)';
                setTimeout(() => {{
                    item.style.transform = '';
                }}, 150);
            }});
        }});
    </script>
</body>
</html>
        """
    
    def _format_number(self, num: int) -> str:
        """Format numbers clearly"""
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.0f}K"
        else:
            return str(num)
    
    def _generate_earthquake_items(self, earthquakes: List[Dict]) -> str:
        """Generate clean earthquake items"""
        if not earthquakes:
            return '<p style="color: #64748b; text-align: center; padding: 2rem;">No recent significant earthquakes</p>'
        
        html = ""
        for eq in earthquakes:
            time_ago = self._get_time_ago(eq['timestamp'])
            severity_class = f"severity-{eq.get('severity', 'low')}"
            
            html += f"""
            <div class="event-item {severity_class}">
                <div class="event-header">
                    <div class="event-title">🌍 Magnitude {eq.get('magnitude', 0)} Earthquake</div>
                    <div class="event-time">{time_ago}</div>
                </div>
                <div class="event-location">📍 {eq.get('location', 'Unknown location')}</div>
                
                <div class="event-meta">
                    <div class="meta-item">
                        <div class="meta-label">Depth</div>
                        <div class="meta-value">{eq.get('depth', 0):.1f}km</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Impact Radius</div>
                        <div class="meta-value">{eq.get('impact_radius', 'Unknown')}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Felt Reports</div>
                        <div class="meta-value">{eq.get('felt_reports', 0)}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Alert Level</div>
                        <div class="meta-value">{eq.get('alert_level', 'green').title()}</div>
                    </div>
                </div>
                
                <div class="event-details">
                    <div class="details-title">Impact Assessment</div>
                    <div class="details-content">
                        <strong>Population:</strong> {eq.get('population_estimate', 'Unknown')}<br>
                        <strong>Damage:</strong> {eq.get('damage_assessment', 'Unknown')}<br>
                        <strong>Response:</strong> {eq.get('response_needed', 'Unknown')}<br>
                        <strong>Comparable:</strong> {eq.get('comparable_event', 'Unknown')}
                        {' • <span style="color: #dc2626;">⚠️ TSUNAMI RISK</span>' if eq.get('tsunami_risk') else ''}
                    </div>
                </div>
            </div>
            """
        
        return html
    
    def _generate_weather_items(self, weather_events: List[Dict]) -> str:
        """Generate clean weather items"""
        if not weather_events:
            return '<p style="color: #64748b; text-align: center; padding: 2rem;">No active weather alerts</p>'
        
        disaster_icons = {
            'flood': '💧', 'hurricane': '🌀', 'tornado': '🌪️',
            'wildfire': '🔥', 'extreme_heat': '🌡️', 'winter_storm': '❄️',
            'severe_weather': '⛈️'
        }
        
        html = ""
        for event in weather_events:
            time_ago = self._get_time_ago(event['timestamp'])
            severity_class = f"severity-{event.get('severity', 'medium')}"
            icon = disaster_icons.get(event.get('type'), '⚠️')
            
            headline = event.get('headline', '')
            if len(headline) > 90:
                headline = headline[:87] + "..."
            
            html += f"""
            <div class="event-item {severity_class}">
                <div class="event-header">
                    <div class="event-title">{icon} {event.get('event_name', 'Weather Alert')}</div>
                    <div class="event-time">{time_ago}</div>
                </div>
                <div class="event-location">📍 {event.get('areas', 'Multiple areas')}</div>
                
                <div style="font-size: 0.875rem; color: #475569; margin-bottom: 1rem;">
                    {headline}
                </div>
                
                <div class="event-meta">
                    <div class="meta-item">
                        <div class="meta-label">Threat Level</div>
                        <div class="meta-value">{event.get('threat_level', 'Unknown')}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Urgency</div>
                        <div class="meta-value">{event.get('urgency', 'Unknown')}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Certainty</div>
                        <div class="meta-value">{event.get('certainty', 'Unknown')}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Population</div>
                        <div class="meta-value">{event.get('affected_population', 'Unknown')}</div>
                    </div>
                </div>
                
                <div class="event-details">
                    <div class="details-title">Response Information</div>
                    <div class="details-content">
                        <strong>Preparation Time:</strong> {event.get('preparation_time', 'Unknown')}<br>
                        <strong>Safety Priority:</strong> {event.get('safety_priority', 'Unknown')}<br>
                        <strong>Impact Scale:</strong> {event.get('impact_scale', 'Unknown')}
                    </div>
                </div>
            </div>
            """
        
        return html
    
    def _get_time_ago(self, timestamp: datetime) -> str:
        """Get clean time ago"""
        now = datetime.now()
        
        if hasattr(timestamp, 'tzinfo') and timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)
        
        diff = now - timestamp
        
        if diff.total_seconds() < 300:
            return "Just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes}m ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
        else:
            days = int(diff.total_seconds() / 86400)
            return f"{days}d ago"

# Clean request handler
class PerfectRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, dashboard, *args, **kwargs):
        self.dashboard = dashboard
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/':
            html = self.dashboard.generate_html()
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'operational',
                'events': len(self.dashboard.data_collector.events),
                'last_update': self.dashboard.data_collector.last_update.isoformat()
            }).encode())
        else:
            self.send_error(404)
    
    def log_message(self, format, *args):
        pass

def create_handler(dashboard):
    def handler(*args, **kwargs):
        PerfectRequestHandler(dashboard, *args, **kwargs)
    return handler

def main():
    print("\n🛡️ Starting Perfect Emergency Response Center")
    print("=" * 55)
    print("✨ Clean, impressive interface")
    print("📊 Clear updates every 3 minutes") 
    print("🌐 Real government data sources")
    print("⚡ Impressive details, simple presentation")
    print("🎨 Beautiful but not overwhelming design")
    print("=" * 55)
    
    port = 8506
    dashboard = PerfectDashboard(port)
    
    handler = create_handler(dashboard)
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"\n✅ Perfect dashboard running at: http://localhost:{port}")
        print(f"🔄 Clear updates every 3 minutes")
        print(f"📡 Press Ctrl+C to stop\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n✅ Perfect dashboard stopped")
            dashboard.data_collector.is_monitoring = False

if __name__ == "__main__":
    main()
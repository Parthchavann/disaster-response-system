#!/usr/bin/env python3
"""
Real-Time Disaster Data Feeds Integration
Connects to live government and public data sources
"""

import json
import time
import requests
from datetime import datetime, timedelta
import threading
from typing import Dict, List, Any
import uuid

class RealTimeDataFeeds:
    """Aggregate real-time disaster data from multiple sources"""
    
    def __init__(self):
        self.active_feeds = {}
        self.latest_events = []
        self.feed_status = {}
        
        # API endpoints for real data
        self.data_sources = {
            'usgs_earthquakes': {
                'url': 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson',
                'name': 'USGS Earthquake Feed',
                'type': 'earthquake',
                'update_interval': 300,  # 5 minutes
                'enabled': True
            },
            'noaa_weather': {
                'url': 'https://api.weather.gov/alerts/active',
                'name': 'NOAA Weather Alerts',
                'type': 'weather',
                'update_interval': 180,  # 3 minutes
                'enabled': True
            },
            'nasa_fires': {
                'url': 'https://firms.modaps.eosdis.nasa.gov/api/country/csv/[API_KEY]/VIIRS_SNPP_NRT/USA/1',
                'name': 'NASA Fire Information',
                'type': 'fire',
                'update_interval': 600,  # 10 minutes
                'enabled': False,  # Requires API key
                'note': 'Requires NASA FIRMS API key'
            },
            'emergency_alerts': {
                'url': 'https://api.weather.gov/alerts/active?status=actual&message_type=alert',
                'name': 'Emergency Alert System',
                'type': 'emergency',
                'update_interval': 120,  # 2 minutes
                'enabled': True
            }
        }
    
    def start_real_time_monitoring(self):
        """Start monitoring all enabled real-time feeds"""
        print("🌍 Starting Real-Time Disaster Monitoring...")
        print("=" * 50)
        
        for feed_id, config in self.data_sources.items():
            if config['enabled']:
                print(f"✅ Starting {config['name']}")
                thread = threading.Thread(
                    target=self._monitor_feed,
                    args=(feed_id, config),
                    daemon=True
                )
                thread.start()
                self.feed_status[feed_id] = {
                    'status': 'running',
                    'last_update': None,
                    'events_count': 0,
                    'errors': 0
                }
            else:
                print(f"⏸️  {config['name']} - {config.get('note', 'Disabled')}")
        
        print("=" * 50)
        print("📡 Real-time monitoring active!")
        return True
    
    def _monitor_feed(self, feed_id: str, config: Dict):
        """Monitor a specific data feed"""
        while True:
            try:
                if feed_id == 'usgs_earthquakes':
                    events = self._fetch_earthquake_data(config['url'])
                elif feed_id == 'noaa_weather':
                    events = self._fetch_weather_alerts(config['url'])
                elif feed_id == 'emergency_alerts':
                    events = self._fetch_emergency_alerts(config['url'])
                else:
                    events = []
                
                if events:
                    self._process_new_events(feed_id, events)
                    self.feed_status[feed_id]['events_count'] += len(events)
                
                self.feed_status[feed_id]['last_update'] = datetime.now().isoformat()
                self.feed_status[feed_id]['status'] = 'healthy'
                
            except Exception as e:
                print(f"❌ Error in {config['name']}: {e}")
                self.feed_status[feed_id]['errors'] += 1
                self.feed_status[feed_id]['status'] = 'error'
            
            time.sleep(config['update_interval'])
    
    def _fetch_earthquake_data(self, url: str) -> List[Dict]:
        """Fetch real-time earthquake data from USGS"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            events = []
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                coords = feature.get('geometry', {}).get('coordinates', [])
                
                # Only include significant earthquakes (magnitude 3.0+)
                magnitude = props.get('mag', 0)
                if magnitude >= 3.0:
                    event = {
                        'event_id': f"usgs_{props.get('ids', str(uuid.uuid4())[:8])}",
                        'source': 'USGS Real-Time',
                        'type': 'earthquake',
                        'title': props.get('title', 'Earthquake'),
                        'magnitude': magnitude,
                        'location': {
                            'name': props.get('place', 'Unknown'),
                            'lat': coords[1] if len(coords) > 1 else None,
                            'lon': coords[0] if len(coords) > 0 else None,
                            'depth': coords[2] if len(coords) > 2 else None
                        },
                        'timestamp': datetime.fromtimestamp(props.get('time', 0) / 1000).isoformat(),
                        'url': props.get('url'),
                        'severity': self._calculate_earthquake_severity(magnitude),
                        'raw_data': props
                    }
                    events.append(event)
            
            return events
            
        except Exception as e:
            print(f"Error fetching earthquake data: {e}")
            return []
    
    def _fetch_weather_alerts(self, url: str) -> List[Dict]:
        """Fetch real-time weather alerts from NOAA"""
        try:
            headers = {'User-Agent': 'DisasterResponseSystem/1.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            events = []
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                
                # Filter for severe weather events
                event_type = props.get('event', '').lower()
                if any(keyword in event_type for keyword in [
                    'tornado', 'hurricane', 'flood', 'fire', 'severe', 'warning', 'watch'
                ]):
                    event = {
                        'event_id': f"noaa_{props.get('id', str(uuid.uuid4())[:8])}",
                        'source': 'NOAA Weather Service',
                        'type': self._classify_weather_event(event_type),
                        'title': props.get('headline', 'Weather Alert'),
                        'description': props.get('description', ''),
                        'event_type': props.get('event'),
                        'severity_level': props.get('severity'),
                        'urgency': props.get('urgency'),
                        'certainty': props.get('certainty'),
                        'areas': props.get('areaDesc', ''),
                        'onset': props.get('onset'),
                        'expires': props.get('expires'),
                        'timestamp': props.get('sent', datetime.now().isoformat()),
                        'severity': self._calculate_weather_severity(props),
                        'raw_data': props
                    }
                    events.append(event)
            
            return events
            
        except Exception as e:
            print(f"Error fetching weather alerts: {e}")
            return []
    
    def _fetch_emergency_alerts(self, url: str) -> List[Dict]:
        """Fetch emergency alerts"""
        try:
            headers = {'User-Agent': 'DisasterResponseSystem/1.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            events = []
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                
                # Filter for actual emergency alerts
                if props.get('messageType') == 'Alert' and props.get('status') == 'Actual':
                    event = {
                        'event_id': f"eas_{props.get('id', str(uuid.uuid4())[:8])}",
                        'source': 'Emergency Alert System',
                        'type': 'emergency',
                        'title': props.get('headline', 'Emergency Alert'),
                        'description': props.get('description', ''),
                        'event_type': props.get('event'),
                        'severity_level': props.get('severity'),
                        'urgency': props.get('urgency'),
                        'areas': props.get('areaDesc', ''),
                        'timestamp': props.get('sent', datetime.now().isoformat()),
                        'severity': props.get('severity', 'medium').lower(),
                        'raw_data': props
                    }
                    events.append(event)
            
            return events
            
        except Exception as e:
            print(f"Error fetching emergency alerts: {e}")
            return []
    
    def _calculate_earthquake_severity(self, magnitude: float) -> str:
        """Calculate earthquake severity based on magnitude"""
        if magnitude >= 7.0:
            return 'critical'
        elif magnitude >= 6.0:
            return 'high'
        elif magnitude >= 4.5:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_weather_severity(self, props: Dict) -> str:
        """Calculate weather event severity"""
        severity = props.get('severity', '').lower()
        urgency = props.get('urgency', '').lower()
        certainty = props.get('certainty', '').lower()
        
        if severity == 'extreme' or urgency == 'immediate':
            return 'critical'
        elif severity == 'severe' or urgency == 'expected':
            return 'high'
        elif severity == 'moderate':
            return 'medium'
        else:
            return 'low'
    
    def _classify_weather_event(self, event_type: str) -> str:
        """Classify weather event type"""
        event_type = event_type.lower()
        
        if any(word in event_type for word in ['tornado', 'funnel']):
            return 'tornado'
        elif any(word in event_type for word in ['hurricane', 'typhoon', 'cyclone']):
            return 'hurricane'
        elif any(word in event_type for word in ['flood', 'flash flood']):
            return 'flood'
        elif any(word in event_type for word in ['fire', 'red flag']):
            return 'fire'
        elif any(word in event_type for word in ['thunderstorm', 'severe']):
            return 'severe_weather'
        else:
            return 'weather_alert'
    
    def _process_new_events(self, feed_id: str, events: List[Dict]):
        """Process and store new events"""
        for event in events:
            # Check if event is recent (within last hour)
            try:
                event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                if datetime.now() - event_time.replace(tzinfo=None) <= timedelta(hours=1):
                    self.latest_events.append(event)
                    print(f"🚨 NEW {event['type'].upper()}: {event['title']}")
            except:
                # If timestamp parsing fails, still include the event
                self.latest_events.append(event)
        
        # Keep only last 100 events
        if len(self.latest_events) > 100:
            self.latest_events = self.latest_events[-100:]
    
    def get_recent_events(self, limit: int = 20) -> List[Dict]:
        """Get recent real-time events"""
        return self.latest_events[-limit:] if self.latest_events else []
    
    def get_feed_status(self) -> Dict:
        """Get status of all data feeds"""
        return {
            'feeds': self.feed_status,
            'total_events': len(self.latest_events),
            'last_update': datetime.now().isoformat(),
            'active_feeds': len([f for f in self.feed_status.values() if f['status'] == 'healthy'])
        }
    
    def get_events_by_type(self, event_type: str) -> List[Dict]:
        """Get events filtered by type"""
        return [event for event in self.latest_events if event.get('type') == event_type]
    
    def get_severe_events(self) -> List[Dict]:
        """Get only high severity events"""
        return [event for event in self.latest_events 
                if event.get('severity') in ['high', 'critical']]

def main():
    """Demo of real-time data feeds"""
    feeds = RealTimeDataFeeds()
    
    print("🌍 Real-Time Disaster Data Monitoring System")
    print("=" * 50)
    print("📡 Available Data Sources:")
    
    for feed_id, config in feeds.data_sources.items():
        status = "✅ ENABLED" if config['enabled'] else "⏸️  DISABLED"
        print(f"  {status} - {config['name']} ({config['type']})")
        if not config['enabled'] and 'note' in config:
            print(f"    Note: {config['note']}")
    
    print("\n🚀 Starting real-time monitoring...")
    feeds.start_real_time_monitoring()
    
    # Keep the demo running and show periodic updates
    try:
        while True:
            time.sleep(30)  # Update every 30 seconds
            
            # Show status update
            status = feeds.get_feed_status()
            recent_events = feeds.get_recent_events(5)
            
            print(f"\n📊 Status Update - {datetime.now().strftime('%H:%M:%S')}")
            print(f"   Active Feeds: {status['active_feeds']}")
            print(f"   Total Events: {status['total_events']}")
            print(f"   Recent Events: {len(recent_events)}")
            
            if recent_events:
                print("   Latest:")
                for event in recent_events[-3:]:
                    print(f"     🚨 {event['type']}: {event['title'][:50]}...")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping real-time monitoring...")
        print("✅ Monitoring stopped")

if __name__ == "__main__":
    main()
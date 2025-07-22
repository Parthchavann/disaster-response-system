"""
Advanced Alerting and Monitoring Rules for Disaster Response System
Custom monitoring logic for disaster detection and system health
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import json
import asyncio
from dataclasses import dataclass
from enum import Enum
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import requests
import websocket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    DISASTER_EVENT = "disaster_event"
    SYSTEM_HEALTH = "system_health"
    PERFORMANCE = "performance"
    SECURITY = "security"

@dataclass
class Alert:
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    timestamp: datetime
    metadata: Dict[str, Any]
    resolved: bool = False
    acknowledgments: List[str] = None

class DisasterAlertManager:
    """Advanced alerting system for disaster response"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.active_alerts = {}
        self.alert_history = []
        
        # Alert thresholds
        self.disaster_thresholds = {
            'critical_event_threshold': 5,  # Number of critical events per hour
            'high_event_rate': 20,          # Events per minute
            'confidence_threshold': 0.8,    # Minimum confidence for auto-alerts
            'geographic_cluster_size': 3,   # Minimum events in cluster
            'time_window_minutes': 30       # Time window for clustering
        }
        
        # System health thresholds
        self.system_thresholds = {
            'api_error_rate': 0.05,         # 5% error rate
            'response_time_p95': 2000,      # 2 seconds
            'memory_usage': 0.85,           # 85% memory usage
            'cpu_usage': 0.80,              # 80% CPU usage
            'disk_usage': 0.90              # 90% disk usage
        }
        
        # Notification channels
        self.notification_channels = self._setup_notification_channels()
        
        logger.info("Alert manager initialized")
    
    def _setup_notification_channels(self) -> Dict[str, Any]:
        """Setup notification channels"""
        channels = {}
        
        # Email notifications
        if self.config.get('email'):
            channels['email'] = EmailNotifier(self.config['email'])
        
        # Slack notifications
        if self.config.get('slack'):
            channels['slack'] = SlackNotifier(self.config['slack'])
        
        # SMS notifications
        if self.config.get('sms'):
            channels['sms'] = SMSNotifier(self.config['sms'])
        
        # Webhook notifications
        if self.config.get('webhook'):
            channels['webhook'] = WebhookNotifier(self.config['webhook'])
        
        return channels
    
    def check_disaster_patterns(self, events: List[Dict[str, Any]]) -> List[Alert]:
        """Check for disaster event patterns and create alerts"""
        alerts = []
        
        if not events:
            return alerts
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(events)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Check for critical event spike
        critical_alerts = self._check_critical_event_spike(df)
        alerts.extend(critical_alerts)
        
        # Check for geographic clustering
        cluster_alerts = self._check_geographic_clustering(df)
        alerts.extend(cluster_alerts)
        
        # Check for multi-modal confirmation
        multimodal_alerts = self._check_multimodal_confirmation(df)
        alerts.extend(multimodal_alerts)
        
        # Check for escalating severity
        escalation_alerts = self._check_severity_escalation(df)
        alerts.extend(escalation_alerts)
        
        return alerts
    
    def _check_critical_event_spike(self, df: pd.DataFrame) -> List[Alert]:
        """Check for spike in critical disaster events"""
        alerts = []
        
        # Get events from last hour
        last_hour = datetime.now() - timedelta(hours=1)
        recent_events = df[df['timestamp'] > last_hour]
        
        # Count critical events
        critical_events = recent_events[
            recent_events['severity'].isin(['high', 'critical'])
        ]
        
        if len(critical_events) >= self.disaster_thresholds['critical_event_threshold']:
            alert = Alert(
                id=f"critical_spike_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                type=AlertType.DISASTER_EVENT,
                severity=AlertSeverity.CRITICAL,
                title="Critical Disaster Event Spike Detected",
                description=f"Detected {len(critical_events)} critical disaster events in the last hour",
                timestamp=datetime.now(),
                metadata={
                    'event_count': len(critical_events),
                    'event_types': critical_events['event_type'].value_counts().to_dict(),
                    'affected_locations': critical_events['location'].tolist(),
                    'time_window': '1 hour'
                }
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_geographic_clustering(self, df: pd.DataFrame) -> List[Alert]:
        """Check for geographic clustering of disaster events"""
        alerts = []
        
        # Group events by approximate location (rounded coordinates)
        df['lat_rounded'] = df['location'].apply(
            lambda x: round(x.get('lat', 0), 1) if isinstance(x, dict) else 0
        )
        df['lon_rounded'] = df['location'].apply(
            lambda x: round(x.get('lon', 0), 1) if isinstance(x, dict) else 0
        )
        
        # Find clusters
        location_groups = df.groupby(['lat_rounded', 'lon_rounded']).size()
        large_clusters = location_groups[
            location_groups >= self.disaster_thresholds['geographic_cluster_size']
        ]
        
        for (lat, lon), count in large_clusters.items():
            cluster_events = df[
                (df['lat_rounded'] == lat) & (df['lon_rounded'] == lon)
            ]
            
            alert = Alert(
                id=f"geo_cluster_{lat}_{lon}_{datetime.now().strftime('%H%M%S')}",
                type=AlertType.DISASTER_EVENT,
                severity=AlertSeverity.HIGH,
                title="Geographic Disaster Cluster Detected",
                description=f"Detected cluster of {count} disaster events at location ({lat}, {lon})",
                timestamp=datetime.now(),
                metadata={
                    'cluster_size': count,
                    'location': {'lat': lat, 'lon': lon},
                    'event_types': cluster_events['event_type'].value_counts().to_dict(),
                    'severity_distribution': cluster_events['severity'].value_counts().to_dict()
                }
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_multimodal_confirmation(self, df: pd.DataFrame) -> List[Alert]:
        """Check for events confirmed by multiple data sources"""
        alerts = []
        
        # Group by location and time window
        time_window = timedelta(minutes=self.disaster_thresholds['time_window_minutes'])
        
        for _, event in df.iterrows():
            event_time = event['timestamp']
            event_loc = event['location']
            
            if not isinstance(event_loc, dict):
                continue
            
            # Find nearby events in time and space
            nearby_events = df[
                (abs(df['timestamp'] - event_time) < time_window) &
                (df.index != event.name)  # Exclude the event itself
            ]
            
            if len(nearby_events) >= 2:  # At least 2 other sources
                # Check if different sources confirm same event type
                same_type_sources = nearby_events[
                    nearby_events['event_type'] == event['event_type']
                ]['source'].unique()
                
                if len(same_type_sources) >= 2:
                    alert = Alert(
                        id=f"multimodal_{event.name}_{datetime.now().strftime('%H%M%S')}",
                        type=AlertType.DISASTER_EVENT,
                        severity=AlertSeverity.HIGH,
                        title="Multi-Source Disaster Confirmation",
                        description=f"{event['event_type']} confirmed by {len(same_type_sources)} independent sources",
                        timestamp=datetime.now(),
                        metadata={
                            'event_type': event['event_type'],
                            'confirming_sources': same_type_sources.tolist(),
                            'location': event_loc,
                            'confidence_boost': True
                        }
                    )
                    alerts.append(alert)
        
        return alerts
    
    def _check_severity_escalation(self, df: pd.DataFrame) -> List[Alert]:
        """Check for escalating severity patterns"""
        alerts = []
        
        # Sort by timestamp
        df_sorted = df.sort_values('timestamp')
        
        # Check for severity escalation in same location
        for location_key in df_sorted['location'].apply(
            lambda x: f"{x.get('lat', 0):.1f}_{x.get('lon', 0):.1f}" if isinstance(x, dict) else "unknown"
        ).unique():
            
            location_events = df_sorted[
                df_sorted['location'].apply(
                    lambda x: f"{x.get('lat', 0):.1f}_{x.get('lon', 0):.1f}" if isinstance(x, dict) else "unknown"
                ) == location_key
            ]
            
            if len(location_events) >= 3:
                # Check if severity is escalating
                severity_map = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
                severities = location_events['severity'].map(severity_map)
                
                # Check for increasing trend
                if self._is_escalating(severities.tolist()):
                    alert = Alert(
                        id=f"escalation_{location_key}_{datetime.now().strftime('%H%M%S')}",
                        type=AlertType.DISASTER_EVENT,
                        severity=AlertSeverity.HIGH,
                        title="Disaster Severity Escalation Detected",
                        description=f"Escalating disaster severity pattern detected at location {location_key}",
                        timestamp=datetime.now(),
                        metadata={
                            'location_key': location_key,
                            'severity_progression': location_events['severity'].tolist(),
                            'event_count': len(location_events),
                            'time_span': str(location_events['timestamp'].max() - location_events['timestamp'].min())
                        }
                    )
                    alerts.append(alert)
        
        return alerts
    
    def _is_escalating(self, values: List[int]) -> bool:
        """Check if values show escalating trend"""
        if len(values) < 3:
            return False
        
        increases = sum(1 for i in range(1, len(values)) if values[i] > values[i-1])
        return increases >= len(values) // 2
    
    def check_system_health(self, metrics: Dict[str, float]) -> List[Alert]:
        """Check system health metrics and create alerts"""
        alerts = []
        
        # Check API error rate
        if metrics.get('api_error_rate', 0) > self.system_thresholds['api_error_rate']:
            alerts.append(Alert(
                id=f"api_errors_{datetime.now().strftime('%H%M%S')}",
                type=AlertType.SYSTEM_HEALTH,
                severity=AlertSeverity.HIGH,
                title="High API Error Rate",
                description=f"API error rate is {metrics['api_error_rate']:.2%}",
                timestamp=datetime.now(),
                metadata={'error_rate': metrics['api_error_rate']}
            ))
        
        # Check response time
        if metrics.get('response_time_p95', 0) > self.system_thresholds['response_time_p95']:
            alerts.append(Alert(
                id=f"response_time_{datetime.now().strftime('%H%M%S')}",
                type=AlertType.PERFORMANCE,
                severity=AlertSeverity.MEDIUM,
                title="High Response Time",
                description=f"95th percentile response time is {metrics['response_time_p95']:.0f}ms",
                timestamp=datetime.now(),
                metadata={'response_time_p95': metrics['response_time_p95']}
            ))
        
        # Check resource usage
        for resource in ['memory_usage', 'cpu_usage', 'disk_usage']:
            if metrics.get(resource, 0) > self.system_thresholds[resource]:
                severity = AlertSeverity.CRITICAL if metrics[resource] > 0.95 else AlertSeverity.HIGH
                alerts.append(Alert(
                    id=f"{resource}_{datetime.now().strftime('%H%M%S')}",
                    type=AlertType.SYSTEM_HEALTH,
                    severity=severity,
                    title=f"High {resource.replace('_', ' ').title()}",
                    description=f"{resource.replace('_', ' ').title()} is at {metrics[resource]:.1%}",
                    timestamp=datetime.now(),
                    metadata={resource: metrics[resource]}
                ))
        
        return alerts
    
    async def send_alert(self, alert: Alert):
        """Send alert through configured notification channels"""
        
        # Store alert
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)
        
        # Determine which channels to use based on severity
        channels_to_use = []
        
        if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
            channels_to_use = list(self.notification_channels.keys())
        elif alert.severity == AlertSeverity.MEDIUM:
            channels_to_use = ['email', 'slack']
        else:
            channels_to_use = ['email']
        
        # Send notifications
        for channel_name in channels_to_use:
            if channel_name in self.notification_channels:
                try:
                    await self.notification_channels[channel_name].send(alert)
                    logger.info(f"Alert {alert.id} sent via {channel_name}")
                except Exception as e:
                    logger.error(f"Failed to send alert via {channel_name}: {e}")
    
    def acknowledge_alert(self, alert_id: str, acknowledger: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            if alert.acknowledgments is None:
                alert.acknowledgments = []
            alert.acknowledgments.append(acknowledger)
            logger.info(f"Alert {alert_id} acknowledged by {acknowledger}")
            return True
        return False
    
    def resolve_alert(self, alert_id: str, resolver: str) -> bool:
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            del self.active_alerts[alert_id]
            logger.info(f"Alert {alert_id} resolved by {resolver}")
            return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert status"""
        active_alerts = list(self.active_alerts.values())
        
        summary = {
            'total_active': len(active_alerts),
            'by_severity': {},
            'by_type': {},
            'oldest_alert': None,
            'newest_alert': None
        }
        
        if active_alerts:
            # Count by severity
            for severity in AlertSeverity:
                count = len([a for a in active_alerts if a.severity == severity])
                summary['by_severity'][severity.value] = count
            
            # Count by type
            for alert_type in AlertType:
                count = len([a for a in active_alerts if a.type == alert_type])
                summary['by_type'][alert_type.value] = count
            
            # Find oldest and newest
            sorted_alerts = sorted(active_alerts, key=lambda x: x.timestamp)
            summary['oldest_alert'] = sorted_alerts[0].timestamp.isoformat()
            summary['newest_alert'] = sorted_alerts[-1].timestamp.isoformat()
        
        return summary

class EmailNotifier:
    """Email notification handler"""
    
    def __init__(self, config: Dict[str, str]):
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.from_email = config.get('from_email', self.username)
        self.to_emails = config.get('to_emails', [])
    
    async def send(self, alert: Alert):
        """Send email notification"""
        
        msg = MimeMultipart()
        msg['From'] = self.from_email
        msg['To'] = ', '.join(self.to_emails)
        msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
        
        body = f"""
        Alert Details:
        
        Type: {alert.type.value}
        Severity: {alert.severity.value}
        Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        
        Description:
        {alert.description}
        
        Metadata:
        {json.dumps(alert.metadata, indent=2)}
        
        Alert ID: {alert.id}
        """
        
        msg.attach(MimeText(body, 'plain'))
        
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise

class SlackNotifier:
    """Slack notification handler"""
    
    def __init__(self, config: Dict[str, str]):
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel', '#alerts')
    
    async def send(self, alert: Alert):
        """Send Slack notification"""
        
        color_map = {
            AlertSeverity.LOW: 'good',
            AlertSeverity.MEDIUM: 'warning', 
            AlertSeverity.HIGH: 'danger',
            AlertSeverity.CRITICAL: 'danger'
        }
        
        payload = {
            'channel': self.channel,
            'attachments': [{
                'color': color_map.get(alert.severity, 'danger'),
                'title': alert.title,
                'text': alert.description,
                'fields': [
                    {'title': 'Severity', 'value': alert.severity.value, 'short': True},
                    {'title': 'Type', 'value': alert.type.value, 'short': True},
                    {'title': 'Time', 'value': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'short': True},
                    {'title': 'Alert ID', 'value': alert.id, 'short': True}
                ],
                'footer': 'Disaster Response System'
            }]
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            raise

class SMSNotifier:
    """SMS notification handler (using Twilio)"""
    
    def __init__(self, config: Dict[str, str]):
        self.account_sid = config.get('account_sid')
        self.auth_token = config.get('auth_token')
        self.from_number = config.get('from_number')
        self.to_numbers = config.get('to_numbers', [])
    
    async def send(self, alert: Alert):
        """Send SMS notification"""
        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            
            message_text = f"[{alert.severity.value.upper()}] {alert.title}\n{alert.description[:100]}..."
            
            for number in self.to_numbers:
                client.messages.create(
                    body=message_text,
                    from_=self.from_number,
                    to=number
                )
        except ImportError:
            logger.error("Twilio package not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            raise

class WebhookNotifier:
    """Generic webhook notification handler"""
    
    def __init__(self, config: Dict[str, str]):
        self.url = config.get('url')
        self.headers = config.get('headers', {})
    
    async def send(self, alert: Alert):
        """Send webhook notification"""
        
        payload = {
            'alert_id': alert.id,
            'type': alert.type.value,
            'severity': alert.severity.value,
            'title': alert.title,
            'description': alert.description,
            'timestamp': alert.timestamp.isoformat(),
            'metadata': alert.metadata
        }
        
        try:
            response = requests.post(self.url, json=payload, headers=self.headers)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            raise

def main():
    """Test the alerting system"""
    
    # Configuration
    config = {
        'email': {
            'username': 'alerts@disaster-response.com',
            'password': 'your-app-password',
            'to_emails': ['admin@disaster-response.com']
        },
        'slack': {
            'webhook_url': 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        }
    }
    
    # Initialize alert manager
    alert_manager = DisasterAlertManager(config)
    
    # Test disaster pattern detection
    test_events = [
        {
            'event_id': 'test_001',
            'event_type': 'flood',
            'severity': 'critical',
            'timestamp': datetime.now().isoformat(),
            'location': {'lat': 25.7617, 'lon': -80.1918},
            'source': 'social_media'
        },
        {
            'event_id': 'test_002',
            'event_type': 'flood',
            'severity': 'high',
            'timestamp': datetime.now().isoformat(),
            'location': {'lat': 25.7617, 'lon': -80.1918},
            'source': 'weather_sensor'
        }
    ]
    
    # Check for disaster patterns
    disaster_alerts = alert_manager.check_disaster_patterns(test_events)
    print(f"Generated {len(disaster_alerts)} disaster alerts")
    
    # Test system health monitoring
    test_metrics = {
        'api_error_rate': 0.08,  # 8% error rate (above threshold)
        'response_time_p95': 2500,  # 2.5 seconds (above threshold)
        'memory_usage': 0.75,  # 75% memory usage
        'cpu_usage': 0.85,  # 85% CPU usage (above threshold)
    }
    
    health_alerts = alert_manager.check_system_health(test_metrics)
    print(f"Generated {len(health_alerts)} system health alerts")
    
    # Print alert summary
    all_alerts = disaster_alerts + health_alerts
    for alert in all_alerts:
        print(f"Alert: {alert.title} [{alert.severity.value}]")
        print(f"  Description: {alert.description}")
        print(f"  Metadata: {alert.metadata}")
        print()

if __name__ == "__main__":
    main()
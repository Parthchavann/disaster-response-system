"""
Streamlit Frontend Dashboard for Disaster Response System
Real-time visualization and monitoring dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
import time
from datetime import datetime, timedelta
import websocket
import threading
from typing import Dict, List, Any
import base64
from PIL import Image
import io

# Page configuration
st.set_page_config(
    page_title="Disaster Response Dashboard",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
API_BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"

# Initialize session state
if 'events' not in st.session_state:
    st.session_state.events = []
if 'alerts' not in st.session_state:
    st.session_state.alerts = []
if 'connected' not in st.session_state:
    st.session_state.connected = False

class DisasterDashboard:
    """Main dashboard class"""
    
    def __init__(self):
        self.api_url = API_BASE_URL
    
    def make_api_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """Make API request to backend"""
        try:
            url = f"{self.api_url}{endpoint}"
            
            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(url, json=data)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            st.error(f"API request failed: {e}")
            return {}
    
    def get_system_stats(self) -> Dict:
        """Get system statistics"""
        return self.make_api_request("/stats")
    
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent disaster events"""
        result = self.make_api_request(f"/recent-events?limit={limit}")
        return result.get('events', [])
    
    def predict_disaster(self, text: str = None, image_data: str = None, 
                        weather_data: Dict = None, location: Dict = None) -> Dict:
        """Predict disaster from input data"""
        request_data = {}
        if text:
            request_data['text'] = text
        if image_data:
            request_data['image_data'] = image_data
        if weather_data:
            request_data['weather_data'] = weather_data
        if location:
            request_data['location'] = location
        
        return self.make_api_request("/predict", method="POST", data=request_data)
    
    def search_events(self, query: str, event_type: str = None, 
                     location: Dict = None, radius_km: float = 50.0) -> Dict:
        """Search for similar events"""
        request_data = {
            "query": query,
            "limit": 20
        }
        if event_type:
            request_data["event_type"] = event_type
        if location:
            request_data["location"] = location
            request_data["radius_km"] = radius_km
        
        return self.make_api_request("/search", method="POST", data=request_data)

def create_disaster_map(events: List[Dict]) -> go.Figure:
    """Create interactive map of disaster events"""
    if not events:
        return go.Figure()
    
    # Extract location data
    lats, lons, texts, colors, sizes = [], [], [], [], []
    
    disaster_colors = {
        'flood': 'blue',
        'fire': 'red', 
        'earthquake': 'brown',
        'hurricane': 'purple',
        'tornado': 'orange',
        'no_disaster': 'green',
        'other_disaster': 'gray'
    }
    
    severity_sizes = {
        'low': 8,
        'medium': 12,
        'high': 16,
        'critical': 20
    }
    
    for event in events:
        if event.get('location'):
            lats.append(event['location'].get('lat', 0))
            lons.append(event['location'].get('lon', 0))
            
            # Create hover text
            hover_text = f"""
            Type: {event.get('top_prediction', 'Unknown')}
            Severity: {event.get('severity', 'Unknown')}
            Confidence: {event.get('confidence_score', 0):.2f}
            Time: {event.get('timestamp', 'Unknown')}
            """
            texts.append(hover_text)
            
            # Color by disaster type
            disaster_type = event.get('top_prediction', 'other_disaster')
            colors.append(disaster_colors.get(disaster_type, 'gray'))
            
            # Size by severity
            severity = event.get('severity', 'low')
            sizes.append(severity_sizes.get(severity, 8))
    
    # Create map
    fig = go.Figure(data=go.Scattermapbox(
        lat=lats,
        lon=lons,
        mode='markers',
        marker=dict(
            size=sizes,
            color=colors,
            opacity=0.7
        ),
        text=texts,
        hovertemplate="%{text}<extra></extra>"
    ))
    
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=np.mean(lats) if lats else 39.8283, 
                       lon=np.mean(lons) if lons else -98.5795),
            zoom=3
        ),
        height=500,
        margin=dict(l=0, r=0, t=0, b=0)
    )
    
    return fig

def create_event_timeline(events: List[Dict]) -> go.Figure:
    """Create timeline of disaster events"""
    if not events:
        return go.Figure()
    
    # Process events for timeline
    df_events = pd.DataFrame(events)
    df_events['timestamp'] = pd.to_datetime(df_events['timestamp'])
    df_events = df_events.sort_values('timestamp')
    
    # Create timeline
    fig = px.scatter(
        df_events, 
        x='timestamp', 
        y='top_prediction',
        color='severity',
        size='confidence_score',
        hover_data=['event_id', 'confidence_score'],
        title="Disaster Events Timeline"
    )
    
    fig.update_layout(
        height=400,
        xaxis_title="Time",
        yaxis_title="Disaster Type"
    )
    
    return fig

def create_severity_distribution(events: List[Dict]) -> go.Figure:
    """Create severity distribution chart"""
    if not events:
        return go.Figure()
    
    # Count by severity
    severity_counts = {}
    for event in events:
        severity = event.get('severity', 'unknown')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    # Create pie chart
    fig = go.Figure(data=[go.Pie(
        labels=list(severity_counts.keys()),
        values=list(severity_counts.values()),
        hole=0.3
    )])
    
    fig.update_layout(
        title="Event Severity Distribution",
        height=300
    )
    
    return fig

def create_disaster_type_chart(events: List[Dict]) -> go.Figure:
    """Create disaster type distribution chart"""
    if not events:
        return go.Figure()
    
    # Count by disaster type
    type_counts = {}
    for event in events:
        disaster_type = event.get('top_prediction', 'unknown')
        type_counts[disaster_type] = type_counts.get(disaster_type, 0) + 1
    
    # Create bar chart
    fig = go.Figure(data=[go.Bar(
        x=list(type_counts.keys()),
        y=list(type_counts.values()),
        marker_color='lightblue'
    )])
    
    fig.update_layout(
        title="Disaster Type Distribution",
        xaxis_title="Disaster Type",
        yaxis_title="Count",
        height=300
    )
    
    return fig

def main():
    """Main dashboard function"""
    
    # Initialize dashboard
    dashboard = DisasterDashboard()
    
    # Sidebar
    st.sidebar.title("🚨 Disaster Response")
    st.sidebar.markdown("---")
    
    # Navigation
    page = st.sidebar.selectbox(
        "Navigate to:",
        ["🏠 Overview", "🔍 Event Analysis", "📊 Predictions", "🔎 Search", "⚙️ Settings"]
    )
    
    # System status in sidebar
    st.sidebar.markdown("### System Status")
    try:
        health = dashboard.make_api_request("/health")
        if health.get('status') == 'healthy':
            st.sidebar.success("✅ System Healthy")
        else:
            st.sidebar.warning("⚠️ System Degraded")
            
        # Component status
        components = health.get('components', {})
        for component, status in components.items():
            color = "🟢" if status == "healthy" else "🔴"
            st.sidebar.text(f"{color} {component.replace('_', ' ').title()}")
            
    except Exception as e:
        st.sidebar.error("🔴 System Offline")
    
    # Main content
    if page == "🏠 Overview":
        show_overview_page(dashboard)
    elif page == "🔍 Event Analysis":
        show_analysis_page(dashboard)
    elif page == "📊 Predictions":
        show_prediction_page(dashboard)
    elif page == "🔎 Search":
        show_search_page(dashboard)
    elif page == "⚙️ Settings":
        show_settings_page(dashboard)

def show_overview_page(dashboard: DisasterDashboard):
    """Show overview dashboard page"""
    
    st.title("🚨 Disaster Response Dashboard")
    st.markdown("Real-time monitoring and analysis of disaster events")
    
    # Get recent events
    recent_events = dashboard.get_recent_events(limit=100)
    
    # System statistics
    stats = dashboard.get_system_stats()
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Events", 
            stats.get('total_events', 0),
            delta=len(recent_events)
        )
    
    with col2:
        active_alerts = len([e for e in recent_events if e.get('severity') in ['high', 'critical']])
        st.metric("Active Alerts", active_alerts)
    
    with col3:
        st.metric(
            "Active Connections",
            stats.get('active_connections', 0)
        )
    
    with col4:
        st.metric(
            "System Uptime",
            "99.9%"  # Placeholder
        )
    
    # Map and timeline
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🗺️ Event Map")
        if recent_events:
            map_fig = create_disaster_map(recent_events[-50:])  # Last 50 events
            st.plotly_chart(map_fig, use_container_width=True)
        else:
            st.info("No recent events to display")
    
    with col2:
        st.subheader("📈 Severity Distribution")
        if recent_events:
            severity_fig = create_severity_distribution(recent_events)
            st.plotly_chart(severity_fig, use_container_width=True)
        else:
            st.info("No data available")
    
    # Timeline
    st.subheader("⏰ Event Timeline")
    if recent_events:
        timeline_fig = create_event_timeline(recent_events[-20:])  # Last 20 events
        st.plotly_chart(timeline_fig, use_container_width=True)
    else:
        st.info("No recent events to display")
    
    # Recent alerts table
    st.subheader("🚨 Recent High-Priority Events")
    high_priority = [e for e in recent_events if e.get('severity') in ['high', 'critical']]
    
    if high_priority:
        df_alerts = pd.DataFrame(high_priority[:10])  # Top 10
        display_cols = ['timestamp', 'top_prediction', 'severity', 'confidence_score']
        available_cols = [col for col in display_cols if col in df_alerts.columns]
        st.dataframe(df_alerts[available_cols], use_container_width=True)
    else:
        st.success("No high-priority alerts")

def show_analysis_page(dashboard: DisasterDashboard):
    """Show detailed event analysis page"""
    
    st.title("🔍 Event Analysis")
    
    # Get recent events
    recent_events = dashboard.get_recent_events(limit=200)
    
    if not recent_events:
        st.warning("No events available for analysis")
        return
    
    # Analysis controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        time_range = st.selectbox(
            "Time Range",
            ["Last 24 hours", "Last 7 days", "Last 30 days", "All time"]
        )
    
    with col2:
        disaster_filter = st.selectbox(
            "Disaster Type",
            ["All"] + list(set([e.get('top_prediction', 'unknown') for e in recent_events]))
        )
    
    with col3:
        severity_filter = st.selectbox(
            "Severity Level",
            ["All", "low", "medium", "high", "critical"]
        )
    
    # Filter events
    filtered_events = recent_events.copy()
    
    if disaster_filter != "All":
        filtered_events = [e for e in filtered_events if e.get('top_prediction') == disaster_filter]
    
    if severity_filter != "All":
        filtered_events = [e for e in filtered_events if e.get('severity') == severity_filter]
    
    st.write(f"Showing {len(filtered_events)} events")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        type_fig = create_disaster_type_chart(filtered_events)
        st.plotly_chart(type_fig, use_container_width=True)
    
    with col2:
        severity_fig = create_severity_distribution(filtered_events)
        st.plotly_chart(severity_fig, use_container_width=True)
    
    # Detailed event table
    st.subheader("📋 Event Details")
    if filtered_events:
        df_events = pd.DataFrame(filtered_events)
        display_cols = ['timestamp', 'event_id', 'top_prediction', 'severity', 'confidence_score']
        available_cols = [col for col in display_cols if col in df_events.columns]
        
        # Add selection
        selected_indices = st.multiselect(
            "Select events to view details:",
            range(len(df_events)),
            format_func=lambda i: f"{df_events.iloc[i].get('event_id', 'Unknown')} - {df_events.iloc[i].get('top_prediction', 'Unknown')}"
        )
        
        st.dataframe(df_events[available_cols], use_container_width=True)
        
        # Show selected event details
        for idx in selected_indices:
            with st.expander(f"Event Details: {df_events.iloc[idx].get('event_id', 'Unknown')}"):
                st.json(df_events.iloc[idx].to_dict())

def show_prediction_page(dashboard: DisasterDashboard):
    """Show prediction interface page"""
    
    st.title("📊 Disaster Prediction")
    st.markdown("Test the disaster detection models with custom input")
    
    # Input methods
    input_method = st.radio(
        "Choose input method:",
        ["Text Input", "Image Upload", "Weather Data", "Combined Input"]
    )
    
    prediction_result = None
    
    if input_method == "Text Input":
        st.subheader("📝 Text Analysis")
        text_input = st.text_area(
            "Enter text describing a potential disaster situation:",
            placeholder="e.g., 'Massive flooding in downtown area, water rising rapidly'"
        )
        
        if st.button("Analyze Text") and text_input:
            with st.spinner("Processing..."):
                prediction_result = dashboard.predict_disaster(text=text_input)
    
    elif input_method == "Image Upload":
        st.subheader("🖼️ Image Analysis")
        uploaded_file = st.file_uploader("Upload disaster image", type=['png', 'jpg', 'jpeg'])
        
        if uploaded_file is not None:
            # Display image
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", use_column_width=True)
            
            if st.button("Analyze Image"):
                # Convert image to base64
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG")
                image_data = base64.b64encode(buffer.getvalue()).decode()
                
                with st.spinner("Processing..."):
                    prediction_result = dashboard.predict_disaster(image_data=image_data)
    
    elif input_method == "Weather Data":
        st.subheader("🌤️ Weather Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            wind_speed = st.number_input("Wind Speed (mph)", min_value=0.0, max_value=200.0, value=10.0)
            precipitation = st.number_input("Precipitation (mm)", min_value=0.0, max_value=100.0, value=5.0)
            temperature = st.number_input("Temperature (°C)", min_value=-50.0, max_value=60.0, value=20.0)
        
        with col2:
            pressure = st.number_input("Pressure (hPa)", min_value=900.0, max_value=1100.0, value=1013.0)
            humidity = st.number_input("Humidity (%)", min_value=0.0, max_value=100.0, value=50.0)
            is_extreme = st.checkbox("Extreme Weather Conditions")
        
        weather_data = {
            'wind_speed_mph': wind_speed,
            'precipitation_mm': precipitation,
            'temperature_c': temperature,
            'pressure_hpa': pressure,
            'humidity_percent': humidity,
            'is_extreme': is_extreme
        }
        
        if st.button("Analyze Weather"):
            with st.spinner("Processing..."):
                prediction_result = dashboard.predict_disaster(weather_data=weather_data)
    
    elif input_method == "Combined Input":
        st.subheader("🔄 Combined Analysis")
        
        # Multiple inputs
        text_input = st.text_area("Text description (optional)")
        
        # Location
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=37.7749)
        with col2:
            lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-122.4194)
        
        location = {'lat': lat, 'lon': lon}
        
        if st.button("Analyze Combined Input"):
            with st.spinner("Processing..."):
                kwargs = {}
                if text_input:
                    kwargs['text'] = text_input
                kwargs['location'] = location
                
                prediction_result = dashboard.predict_disaster(**kwargs)
    
    # Display prediction results
    if prediction_result:
        st.subheader("🎯 Prediction Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Top Prediction", prediction_result.get('top_prediction', 'Unknown'))
        
        with col2:
            confidence = prediction_result.get('confidence_score', 0)
            st.metric("Confidence", f"{confidence:.1%}")
        
        with col3:
            st.metric("Severity", prediction_result.get('severity', 'Unknown'))
        
        # Prediction breakdown
        st.subheader("📊 Prediction Breakdown")
        predictions = prediction_result.get('predictions', {})
        
        # Create bar chart of all predictions
        if predictions:
            pred_df = pd.DataFrame([
                {'Disaster Type': k, 'Probability': v} 
                for k, v in predictions.items()
            ]).sort_values('Probability', ascending=True)
            
            fig = px.bar(
                pred_df, 
                x='Probability', 
                y='Disaster Type',
                orientation='h',
                title="Prediction Probabilities"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Full response
        with st.expander("View Full Response"):
            st.json(prediction_result)

def show_search_page(dashboard: DisasterDashboard):
    """Show event search page"""
    
    st.title("🔎 Event Search")
    st.markdown("Search for similar disaster events")
    
    # Search inputs
    search_query = st.text_input(
        "Search query:",
        placeholder="e.g., 'flooding in Miami'"
    )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        event_type_filter = st.selectbox(
            "Event Type (optional)",
            ["All", "flood", "fire", "earthquake", "hurricane", "tornado", "other_disaster"]
        )
    
    with col2:
        search_lat = st.number_input("Latitude (optional)", value=0.0)
    
    with col3:
        search_lon = st.number_input("Longitude (optional)", value=0.0)
    
    radius = st.slider("Search radius (km)", min_value=1, max_value=1000, value=50)
    
    if st.button("Search Events") and search_query:
        with st.spinner("Searching..."):
            search_params = {
                "query": search_query
            }
            
            if event_type_filter != "All":
                search_params["event_type"] = event_type_filter
            
            if search_lat != 0.0 or search_lon != 0.0:
                search_params["location"] = {"lat": search_lat, "lon": search_lon}
                search_params["radius_km"] = radius
            
            results = dashboard.search_events(**search_params)
            
            if results and results.get('results'):
                st.success(f"Found {results['total_results']} matching events")
                
                # Display results
                for i, result in enumerate(results['results'][:10]):  # Top 10
                    with st.expander(f"Result {i+1} - Score: {result.get('score', 0):.3f}"):
                        if 'event' in result:
                            st.json(result['event'])
                        else:
                            st.json(result)
            else:
                st.warning("No matching events found")

def show_settings_page(dashboard: DisasterDashboard):
    """Show settings page"""
    
    st.title("⚙️ Settings")
    
    st.subheader("🔧 System Configuration")
    
    # API settings
    with st.expander("API Configuration"):
        api_url = st.text_input("API Base URL", value=API_BASE_URL)
        ws_url = st.text_input("WebSocket URL", value=WS_URL)
        
        if st.button("Test Connection"):
            try:
                response = requests.get(f"{api_url}/health")
                if response.status_code == 200:
                    st.success("✅ Connection successful")
                else:
                    st.error("❌ Connection failed")
            except Exception as e:
                st.error(f"❌ Connection error: {e}")
    
    # Display settings
    with st.expander("Display Settings"):
        auto_refresh = st.checkbox("Auto-refresh data", value=True)
        refresh_interval = st.slider("Refresh interval (seconds)", 5, 60, 30)
        max_events = st.number_input("Maximum events to display", 50, 1000, 200)
    
    # Alert settings
    with st.expander("Alert Settings"):
        enable_alerts = st.checkbox("Enable real-time alerts", value=True)
        alert_severity = st.selectbox(
            "Minimum alert severity",
            ["low", "medium", "high", "critical"]
        )
        alert_radius = st.number_input("Alert radius (km)", value=100.0)
    
    # System information
    st.subheader("ℹ️ System Information")
    
    try:
        stats = dashboard.get_system_stats()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Database Statistics:**")
            st.write(f"Total Events: {stats.get('total_events', 'N/A')}")
            st.write(f"Total Locations: {stats.get('total_locations', 'N/A')}")
            st.write(f"Total Reports: {stats.get('total_reports', 'N/A')}")
        
        with col2:
            st.markdown("**System Status:**")
            st.write(f"Active Connections: {stats.get('active_connections', 'N/A')}")
            st.write(f"Active Subscriptions: {stats.get('active_subscriptions', 'N/A')}")
    
    except Exception as e:
        st.error(f"Unable to fetch system information: {e}")

if __name__ == "__main__":
    main()
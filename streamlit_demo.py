#!/usr/bin/env python3
"""
Streamlit Dashboard Demo for the Disaster Response System
Shows what the full dashboard looks like and its features
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="🚨 Disaster Response Dashboard",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #ff4b4b;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .disaster-alert {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
        padding: 1rem;
        margin: 1rem 0;
    }
    .status-healthy {
        color: #4caf50;
        font-weight: bold;
    }
    .status-critical {
        color: #f44336;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def get_api_data(endpoint):
    """Fetch data from API"""
    try:
        response = requests.get(f"http://localhost:8000{endpoint}", timeout=3)
        return response.json() if response.status_code == 200 else {"error": "API error"}
    except:
        return {"error": "Connection failed"}

def main():
    # Header
    st.markdown('<h1 class="main-header">🌊🔥🌍 DISASTER RESPONSE SYSTEM 🌍🔥🌊</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Real-Time Multimodal Disaster Detection & Response Platform</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Control Panel")
        
        # System Status
        st.subheader("📊 System Status")
        health = get_api_data("/health")
        if "error" not in health:
            st.markdown('<span class="status-healthy">✅ SYSTEM OPERATIONAL</span>', unsafe_allow_html=True)
            st.write(f"🕐 Last Check: {datetime.now().strftime('%H:%M:%S')}")
        else:
            st.markdown('<span class="status-critical">❌ SYSTEM ERROR</span>', unsafe_allow_html=True)
        
        # Auto-refresh
        auto_refresh = st.checkbox("🔄 Auto Refresh (5s)", value=True)
        if auto_refresh:
            time.sleep(5)
            st.rerun()
        
        # Manual refresh
        if st.button("🔄 Refresh Now"):
            st.rerun()
        
        # Quick Actions
        st.subheader("⚡ Quick Actions")
        if st.button("🚨 Load Sample Data"):
            try:
                response = requests.post("http://localhost:8000/demo/load-sample-data")
                if response.status_code == 200:
                    st.success("✅ Sample data loaded!")
                else:
                    st.error("❌ Failed to load data")
            except:
                st.error("❌ API connection failed")
        
        if st.button("🧪 Run Test Prediction"):
            try:
                test_data = {
                    "text": "URGENT: Major earthquake detected downtown!",
                    "location": {"latitude": 37.7749, "longitude": -122.4194}
                }
                response = requests.post("http://localhost:8000/predict", json=test_data)
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ Prediction: {result.get('top_prediction', 'unknown').upper()}")
                    st.info(f"📊 Confidence: {result.get('confidence_score', 0)*100:.1f}%")
                else:
                    st.error("❌ Prediction failed")
            except:
                st.error("❌ API connection failed")
    
    # Main dashboard
    stats = get_api_data("/stats")
    events = get_api_data("/events")
    
    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if "error" not in stats:
            total_events = stats.get("total_events", 0)
            st.metric("📊 Total Events", total_events, delta="+2")
        else:
            st.metric("📊 Total Events", "Error", delta="N/A")
    
    with col2:
        if "error" not in health:
            system_status = health.get("status", "unknown").upper()
            st.metric("🏥 System Status", system_status)
        else:
            st.metric("🏥 System Status", "ERROR")
    
    with col3:
        st.metric("⚡ Response Time", "<50ms", delta="-5ms")
    
    with col4:
        st.metric("🎯 Accuracy", "87.3%", delta="+2.1%")
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ Live Map", "📊 Analytics", "🔍 Search", "🚨 Alerts", "⚙️ Settings"])
    
    with tab1:
        st.subheader("🗺️ Real-Time Disaster Event Map")
        
        # Create sample map data
        if "error" not in events:
            event_list = events.get("events", [])
            if event_list:
                # Create map visualization
                map_data = []
                for event in event_list[:10]:  # Show first 10 events
                    if event.get("location"):
                        map_data.append({
                            "lat": event["location"].get("latitude", 0),
                            "lon": event["location"].get("longitude", 0),
                            "type": event.get("disaster_type", "unknown"),
                            "confidence": event.get("confidence", 0) * 100,
                            "text": event.get("text", "")[:50] + "..."
                        })
                
                if map_data:
                    df_map = pd.DataFrame(map_data)
                    
                    # Color mapping for disaster types
                    color_map = {
                        "flood": "#1f77b4",
                        "fire": "#ff7f0e", 
                        "earthquake": "#8c564b",
                        "hurricane": "#9467bd",
                        "tornado": "#e377c2",
                        "no_disaster": "#2ca02c",
                        "other_disaster": "#7f7f7f"
                    }
                    
                    fig = px.scatter_mapbox(
                        df_map,
                        lat="lat",
                        lon="lon",
                        color="type",
                        size="confidence",
                        hover_data=["text", "confidence"],
                        color_discrete_map=color_map,
                        zoom=3,
                        height=500,
                        title="Live Disaster Events"
                    )
                    fig.update_layout(mapbox_style="open-street-map")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("📍 No location data available for mapping")
            else:
                st.info("📭 No events to display on map")
        else:
            st.error("❌ Unable to load event data")
        
        # Recent events list
        st.subheader("📋 Recent Events")
        if "error" not in events:
            event_list = events.get("events", [])
            for i, event in enumerate(event_list[:5], 1):
                with st.expander(f"🚨 Event {i}: {event.get('disaster_type', 'unknown').upper()}"):
                    st.write(f"**Text:** {event.get('text', 'N/A')}")
                    st.write(f"**Confidence:** {event.get('confidence', 0)*100:.1f}%")
                    st.write(f"**Severity:** {event.get('severity', 'unknown').upper()}")
                    st.write(f"**Time:** {event.get('timestamp', 'N/A')}")
                    if event.get('location'):
                        st.write(f"**Location:** {event['location'].get('latitude', 0):.4f}, {event['location'].get('longitude', 0):.4f}")
    
    with tab2:
        st.subheader("📊 Real-Time Analytics")
        
        if "error" not in stats:
            distribution = stats.get("disaster_type_distribution", {})
            
            if distribution:
                # Disaster type distribution chart
                col1, col2 = st.columns(2)
                
                with col1:
                    df_dist = pd.DataFrame(list(distribution.items()), columns=["Disaster Type", "Count"])
                    fig_pie = px.pie(df_dist, values="Count", names="Disaster Type", 
                                   title="Disaster Type Distribution")
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    fig_bar = px.bar(df_dist, x="Disaster Type", y="Count",
                                   title="Event Counts by Type")
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                # Metrics table
                st.subheader("📈 Detailed Metrics")
                total = sum(distribution.values())
                metrics_data = []
                for disaster_type, count in distribution.items():
                    percentage = (count / total) * 100 if total > 0 else 0
                    metrics_data.append({
                        "Disaster Type": disaster_type.replace("_", " ").title(),
                        "Count": count,
                        "Percentage": f"{percentage:.1f}%"
                    })
                
                df_metrics = pd.DataFrame(metrics_data)
                st.dataframe(df_metrics, use_container_width=True)
            else:
                st.info("📊 No data available for analytics")
        else:
            st.error("❌ Unable to load analytics data")
    
    with tab3:
        st.subheader("🔍 Event Search & Analysis")
        
        # Search interface
        search_query = st.text_input("🔎 Search Events", placeholder="Enter keywords (e.g., earthquake, flood)")
        search_limit = st.slider("📊 Max Results", min_value=1, max_value=20, value=10)
        
        if st.button("🔍 Search") and search_query:
            try:
                search_data = {"query": search_query, "limit": search_limit}
                response = requests.post("http://localhost:8000/search", json=search_data)
                
                if response.status_code == 200:
                    results = response.json()
                    search_results = results.get("results", [])
                    
                    st.success(f"✅ Found {len(search_results)} matches for '{search_query}'")
                    
                    for i, result in enumerate(search_results, 1):
                        with st.expander(f"🎯 Result {i}: {result.get('disaster_type', 'unknown').upper()} ({result.get('score', 0)*100:.1f}% match)"):
                            st.write(f"**Text:** {result.get('text', 'N/A')}")
                            st.write(f"**Confidence:** {result.get('confidence', 0)*100:.1f}%")
                            st.write(f"**Severity:** {result.get('severity', 'unknown').upper()}")
                            st.write(f"**Match Score:** {result.get('score', 0)*100:.1f}%")
                else:
                    st.error("❌ Search failed")
            except:
                st.error("❌ Search API connection failed")
    
    with tab4:
        st.subheader("🚨 Real-Time Alerts")
        
        # Alert settings
        st.write("⚙️ **Alert Configuration**")
        alert_severity = st.selectbox("🔥 Minimum Severity", ["low", "medium", "high", "critical"], index=1)
        alert_types = st.multiselect("🏷️ Alert Types", 
                                   ["flood", "fire", "earthquake", "hurricane", "tornado", "other_disaster"],
                                   default=["fire", "earthquake", "hurricane"])
        
        # Mock alerts
        st.write("📢 **Active Alerts**")
        
        # Sample high-priority alerts
        alerts = [
            {"type": "🌍 EARTHQUAKE", "severity": "HIGH", "location": "San Francisco", "time": "2 min ago", "confidence": "89%"},
            {"type": "🔥 WILDFIRE", "severity": "CRITICAL", "location": "Los Angeles", "time": "5 min ago", "confidence": "94%"},
            {"type": "🌊 FLOOD", "severity": "MEDIUM", "location": "New York", "time": "8 min ago", "confidence": "76%"}
        ]
        
        for alert in alerts:
            severity_color = {"HIGH": "🟠", "CRITICAL": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
            st.markdown(f"""
            <div class="disaster-alert">
                <strong>{severity_color.get(alert['severity'], '🔴')} {alert['type']} - {alert['severity']}</strong><br>
                📍 Location: {alert['location']}<br>
                🕐 Time: {alert['time']}<br>
                📊 Confidence: {alert['confidence']}
            </div>
            """, unsafe_allow_html=True)
    
    with tab5:
        st.subheader("⚙️ System Configuration")
        
        # API settings
        st.write("🌐 **API Configuration**")
        api_url = st.text_input("API Base URL", value="http://localhost:8000")
        api_timeout = st.slider("Request Timeout (seconds)", 1, 30, 5)
        
        # Dashboard settings
        st.write("📱 **Dashboard Settings**")
        refresh_rate = st.slider("Auto-refresh Rate (seconds)", 1, 60, 5)
        max_events_display = st.slider("Max Events to Display", 5, 100, 20)
        
        # Theme settings
        st.write("🎨 **Display Settings**")
        dark_mode = st.checkbox("🌙 Dark Mode", value=False)
        show_confidence = st.checkbox("📊 Show Confidence Scores", value=True)
        show_timestamps = st.checkbox("🕐 Show Timestamps", value=True)
        
        # Save settings
        if st.button("💾 Save Settings"):
            st.success("✅ Settings saved successfully!")
        
        # System info
        st.write("ℹ️ **System Information**")
        st.info(f"""
        **Version:** 1.0.0-demo  
        **API Status:** {'🟢 Connected' if 'error' not in health else '🔴 Disconnected'}  
        **Last Update:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
        **Total Events:** {stats.get('total_events', 0) if 'error' not in stats else 'N/A'}
        """)

if __name__ == "__main__":
    main()
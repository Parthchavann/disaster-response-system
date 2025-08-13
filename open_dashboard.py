#!/usr/bin/env python3
"""
Direct Dashboard Opener - Opens the HTML file directly in browser
No server needed, avoids all network issues
"""

import os
import webbrowser
import shutil
import sys

def open_dashboard_directly():
    """Open the dashboard HTML file directly in the browser"""
    
    # Path to the dashboard file
    dashboard_path = r"C:\Users\Parth Chavan\OneDrive\Desktop\premium_dashboard.html"
    
    print("🚨 DISASTER RESPONSE DASHBOARD LAUNCHER")
    print("=" * 60)
    print("📂 Opening dashboard HTML file directly...")
    print(f"📄 File: {dashboard_path}")
    print("=" * 60)
    
    # Check if file exists
    if not os.path.exists(dashboard_path):
        print("❌ Dashboard file not found!")
        print("📝 Creating a new copy...")
        
        # Try to copy from project directory
        source_path = r"C:\Users\Parth Chavan\OneDrive\Desktop\disaster-response-system\premium_dashboard.html"
        if os.path.exists(source_path):
            shutil.copy(source_path, dashboard_path)
            print("✅ Dashboard file created!")
        else:
            print("❌ Could not find source file!")
            return False
    
    # Open the file in default browser
    try:
        # Convert to file:// URL for browser
        file_url = 'file:///' + dashboard_path.replace('\\', '/')
        
        print("🌐 Opening in your default browser...")
        print(f"📍 URL: {file_url}")
        print("=" * 60)
        
        # Open in browser
        webbrowser.open(file_url)
        
        print("✅ Dashboard opened successfully!")
        print("\n📌 IMPORTANT NOTES:")
        print("1. This is the standalone version (no live updates)")
        print("2. All features work except real-time data")
        print("3. You can interact with all UI elements")
        print("\n💡 TIP: Bookmark the page for easy access!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error opening browser: {e}")
        print("\n🔧 MANUAL STEPS:")
        print("1. Open Windows Explorer")
        print("2. Navigate to: C:\\Users\\Parth Chavan\\OneDrive\\Desktop")
        print("3. Double-click: premium_dashboard.html")
        return False

def create_desktop_shortcut():
    """Create a desktop shortcut for easy access"""
    
    shortcut_content = '''[InternetShortcut]
URL=file:///C:/Users/Parth%20Chavan/OneDrive/Desktop/premium_dashboard.html
IconIndex=0
IconFile=C:\\Windows\\System32\\SHELL32.dll
'''
    
    shortcut_path = r"C:\Users\Parth Chavan\OneDrive\Desktop\Disaster Dashboard.url"
    
    try:
        with open(shortcut_path, 'w') as f:
            f.write(shortcut_content)
        print("\n🎯 Desktop shortcut created: 'Disaster Dashboard'")
        print("   Double-click it anytime to open the dashboard!")
    except:
        pass

if __name__ == "__main__":
    print("\n" + "🚨" * 10)
    print("DISASTER RESPONSE DASHBOARD")
    print("🚨" * 10 + "\n")
    
    success = open_dashboard_directly()
    
    if success:
        create_desktop_shortcut()
        print("\n✨ Dashboard is now open in your browser!")
        print("🔄 Refresh the page if needed (F5)")
    else:
        print("\n❌ Automatic opening failed")
        print("📝 Please manually open the file:")
        print("   C:\\Users\\Parth Chavan\\OneDrive\\Desktop\\premium_dashboard.html")
    
    print("\n" + "=" * 60)
    input("Press Enter to exit...")
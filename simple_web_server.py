#!/usr/bin/env python3
"""
Simple Web Server to serve the dashboard HTML file
This will work without any network issues
"""

import http.server
import socketserver
import os
import webbrowser
import threading
import time

def serve_dashboard():
    """Serve the dashboard on a simple HTTP server"""
    
    # Change to the directory containing the HTML file
    os.chdir(r"C:\Users\Parth Chavan\OneDrive\Desktop")
    
    PORT = 8080
    
    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/' or self.path == '/dashboard':
                self.path = '/premium_dashboard.html'
            return super().do_GET()
        
        def log_message(self, format, *args):
            # Custom logging
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")
    
    try:
        with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
            print("🌐 Simple Dashboard Server Starting")
            print("=" * 50)
            print(f"📊 Dashboard URL: http://localhost:{PORT}")
            print(f"📁 Serving from: C:\\Users\\Parth Chavan\\OneDrive\\Desktop")
            print(f"📄 File: premium_dashboard.html")
            print("=" * 50)
            print("✅ Server is ready!")
            print("🌐 Opening browser automatically...")
            print("Press Ctrl+C to stop server")
            print("=" * 50)
            
            # Auto-open browser after 2 seconds
            def open_browser():
                time.sleep(2)
                try:
                    webbrowser.open(f'http://localhost:{PORT}')
                    print("🚀 Browser opened automatically!")
                except:
                    print("⚠️ Could not auto-open browser. Please open manually.")
            
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            # Serve forever
            httpd.serve_forever()
            
    except Exception as e:
        print(f"❌ Server error: {e}")
        print("💡 Try a different port or check if port 8080 is already in use")

if __name__ == "__main__":
    try:
        serve_dashboard()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        input("Press Enter to exit...")
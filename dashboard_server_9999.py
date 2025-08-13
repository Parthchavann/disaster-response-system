#!/usr/bin/env python3
"""
Dashboard Server on Port 9999 (Avoids Airflow conflict on 8080)
"""

import http.server
import socketserver
import os
import webbrowser
import threading
import time

def serve_dashboard():
    """Serve the dashboard on port 9999"""
    
    # Change to the directory containing the HTML file
    os.chdir(r"C:\Users\Parth Chavan\OneDrive\Desktop")
    
    PORT = 9999  # Using 9999 to avoid Airflow on 8080
    
    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/' or self.path == '/dashboard':
                self.path = '/premium_dashboard.html'
            return super().do_GET()
        
        def log_message(self, format, *args):
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")
    
    try:
        with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
            print("🚨 DISASTER RESPONSE DASHBOARD SERVER")
            print("=" * 60)
            print(f"✅ Dashboard URL: http://localhost:{PORT}")
            print(f"📁 Serving: premium_dashboard.html")
            print("=" * 60)
            print("⚠️  NOTE: Airflow is using port 8080")
            print(f"✨ We're using port {PORT} instead")
            print("=" * 60)
            print("🌐 Opening browser to dashboard...")
            print("Press Ctrl+C to stop server")
            print("=" * 60)
            
            # Auto-open browser
            def open_browser():
                time.sleep(2)
                try:
                    webbrowser.open(f'http://localhost:{PORT}')
                    print(f"🚀 Browser opened at http://localhost:{PORT}")
                except:
                    print(f"⚠️ Please manually open: http://localhost:{PORT}")
            
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            httpd.serve_forever()
            
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {PORT} is already in use!")
            print("💡 Trying alternative port 7777...")
            PORT = 7777
            serve_with_port(PORT)
        else:
            print(f"❌ Server error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def serve_with_port(port):
    """Fallback server with different port"""
    os.chdir(r"C:\Users\Parth Chavan\OneDrive\Desktop")
    
    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/' or self.path == '/dashboard':
                self.path = '/premium_dashboard.html'
            return super().do_GET()
    
    with socketserver.TCPServer(("", port), CustomHandler) as httpd:
        print(f"✅ Now serving on port {port}")
        print(f"🌐 Open browser to: http://localhost:{port}")
        webbrowser.open(f'http://localhost:{port}')
        httpd.serve_forever()

if __name__ == "__main__":
    try:
        serve_dashboard()
    except KeyboardInterrupt:
        print("\n🛑 Dashboard server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        input("Press Enter to exit...")
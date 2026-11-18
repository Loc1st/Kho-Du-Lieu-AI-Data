"""Phone sales BI: Python HTTP Server + MVC, http://localhost:8050."""
from http.server import ThreadingHTTPServer
from mvc.controllers.router import MvcRouter
PORT=8050
DashboardHandler=MvcRouter

def main():
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    server=ThreadingHTTPServer(('127.0.0.1',PORT),MvcRouter)
    print('PHONE SALES DATA WAREHOUSE — BUSINESS INTELLIGENCE DASHBOARD')
    print(f'http://localhost:{PORT} · Ctrl+C để dừng')
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()

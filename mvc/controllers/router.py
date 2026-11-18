"""HTTP MVC routing for the local phone sales dashboard."""
import json
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs,urlparse
from sqlalchemy.exc import SQLAlchemyError
from mvc.controllers.etl_controller import EtlController
from mvc.controllers.olap_controller import OlapController
from mvc.controllers.scd2_controller import Scd2Controller
from mvc.controllers.sql_controller import SqlController
from mvc.views.view import render_error,render_html_page,WEB_DIR

class MvcRouter(BaseHTTPRequestHandler):
    def _respond(self,body,content_type,status=200):
        self.send_response(status)
        self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(body)
    def failure(self,exc):
        if isinstance(exc,(ValueError,TypeError,KeyError)):
            body,ct,status=render_error(str(exc),400)
        elif isinstance(exc,SQLAlchemyError):
            logging.error('Database request failed: %s',type(exc).__name__)
            body,ct,status=render_error('Không truy vấn được phone_dw/phone_source. Kiểm tra MariaDB, cấu hình .env và chạy run_all.py. Chi tiết kỹ thuật: '+type(exc).__name__,503)
        else:
            logging.error('Request failed: %s',type(exc).__name__)
            body,ct,status=render_error('Không thể xử lý yêu cầu: '+type(exc).__name__,500)
        self._respond(body,ct,status)
    def do_GET(self):
        parsed=urlparse(self.path);path=parsed.path
        qs={k:v[0] for k,v in parse_qs(parsed.query).items() if v and v[0]}
        try:
            if path in ('/','/index.html'):
                self._respond(*render_html_page());return
            assets={'/app.js':('app.js','text/javascript; charset=utf-8'),'/vendor/chart.umd.min.js':('vendor/chart.umd.min.js','text/javascript; charset=utf-8')}
            if path in assets:
                file,ct=assets[path];self._respond((WEB_DIR/file).read_bytes(),ct);return
            routes={'/api/filters':lambda:OlapController.handle_get_filters(),
            '/api/overview':lambda:OlapController.handle_get_overview(qs),
            '/api/store':lambda:Scd2Controller.handle_get_detail(qs),
            '/api/search_store':lambda:Scd2Controller.handle_search(qs),
            '/api/etl':lambda:EtlController.handle_get_data()}
            if path not in routes:
                self._respond(*render_error('Không tìm thấy tài nguyên',404));return
            self._respond(*routes[path]())
        except Exception as exc:self.failure(exc)
    def do_POST(self):
        try:
            origin=self.headers.get('Origin')
            if origin and urlparse(origin).netloc!=self.headers.get('Host'):
                self._respond(*render_error('Origin không hợp lệ',403));return
            length=int(self.headers.get('Content-Length','0'))
            if not 0<=length<=16384:raise ValueError('Yêu cầu quá lớn')
            payload=json.loads(self.rfile.read(length).decode('utf8') or '{}')
            if not isinstance(payload,dict):raise ValueError('JSON phải là object')
            routes={'/api/scd2_change':lambda:Scd2Controller.handle_change_region(payload),
            '/api/run_tests':lambda:EtlController.handle_run_tests(),
            '/api/sql':lambda:SqlController.handle_execute_sql(payload)}
            path=urlparse(self.path).path
            if path not in routes:self._respond(*render_error('Endpoint không hợp lệ',404));return
            self._respond(*routes[path]())
        except Exception as exc:self.failure(exc)
    def log_message(self,format,*args):return

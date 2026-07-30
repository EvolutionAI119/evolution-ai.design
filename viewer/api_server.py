"""
EVOLUTION_AI API Server
Serves the 3D viewer and provides NURBS generation endpoints
"""
import sys
import json
import time
import numpy as np
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import socketserver

# Add EVO_AI root to path
EVO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(EVO_ROOT))
sys.path.insert(0, str(EVO_ROOT / "core"))

from core.nurbs.surface import NURBSSurface
from core.nurbs.continuity import compute_surface_quality_score
from SUPER_AGENT.evo_agent import EvoAgent, DesignIntentParser


# ============================================================
# API Handler
# ============================================================

class EvoAPIHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for EVOLUTION_AI API"""
    
    def __init__(self, *args, **kwargs):
        # Store agent reference
        self.agent = evo_agent
        super().__init__(*args, directory=str(VIEWER_DIR), **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/api/health':
            self.send_json({'status': 'ok', 'service': 'EVOLUTION_AI', 'version': '1.0'})
        elif self.path == '/api/agent':
            # Agent status
            self.send_json({
                'status': 'running',
                'history_count': len(self.agent.history),
                'capabilities': ['surface_generation', 'quality_assessment', 'design_parsing']
            })
        elif self.path.startswith('/api/result/'):
            idx = int(self.path.split('/')[-1]) - 1
            if 0 <= idx < len(self.agent.history):
                self.send_json(self.agent.history[idx])
            else:
                self.send_error(404, 'Result not found')
        else:
            # Serve static files
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body)
        except:
            self.send_error(400, 'Invalid JSON')
            return
        
        if self.path == '/api/generate':
            self.handle_generate(data)
        elif self.path == '/api/batch_generate':
            self.handle_batch_generate(data)
        elif self.path == '/api/compare':
            self.handle_compare(data)
        elif self.path == '/api/quality':
            self.handle_quality(data)
        else:
            self.send_error(404, 'Unknown endpoint')
    
    def handle_generate(self, data):
        """Generate a surface from design intent"""
        request = data.get('request', '')
        
        start = time.time()
        result = self.agent.run(request)
        elapsed = time.time() - start
        
        response = {
            'success': True,
            'result': result,
            'timing_ms': elapsed * 1000
        }
        self.send_json(response)
    
    def handle_batch_generate(self, data):
        """Batch generate multiple surfaces"""
        requests = data.get('requests', [])
        results = self.agent.batch_run(requests)
        
        self.send_json({'success': True, 'results': results})
    
    def handle_compare(self, data):
        """Compare design results"""
        indices = data.get('indices', [])
        results = [self.agent.history[i] for i in indices if i < len(self.agent.history)]
        comparison = self.agent.compare(results)
        
        self.send_json({'success': True, 'comparison': comparison, 'results': results})
    
    def handle_quality(self, data):
        """Assess quality of a surface"""
        surf_dict = data.get('surface', {})
        
        try:
            surf = NURBSSurface.from_dict(surf_dict)
            quality = compute_surface_quality_score(surf)
            self.send_json({'success': True, 'quality': quality})
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)})
    
    def send_json(self, data):
        """Send JSON response"""
        response = json.dumps(data, ensure_ascii=False, indent=2)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[{time.strftime('%H:%M:%S')}] {args[0]}")


# ============================================================
# Server
# ============================================================

PORT = 8888
VIEWER_DIR = Path(__file__).parent
EVO_ROOT = VIEWER_DIR.parent

# Initialize agent
evo_agent = EvoAgent()

# Threaded HTTP server
class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_server(port=PORT):
    """Start the API server"""
    server = ThreadedHTTPServer(('localhost', port), EvoAPIHandler)
    
    print(f"""
╔══════════════════════════════════════════════╗
║     EVOLUTION_AI API Server                 ║
║     Automotive A-Surface Design System       ║
╠══════════════════════════════════════════════╣
║  API:  http://localhost:{port}               ║
║  Web:  http://localhost:{port}/viewer/index.html ║
║                                              ║
║  Endpoints:                                 ║
║  POST /api/generate    - Generate surface   ║
║  POST /api/batch_generate - Batch generate  ║
║  POST /api/compare     - Compare results    ║
║  POST /api/quality     - Assess quality     ║
║  GET  /api/agent       - Agent status       ║
║  GET  /api/health      - Health check       ║
╚══════════════════════════════════════════════╝
""")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', '-p', type=int, default=PORT)
    args = parser.parse_args()
    
    start_server(args.port)

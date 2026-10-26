#!/usr/bin/env python3
"""Flask web app for browsing benchmark runs."""

from flask import Flask, render_template, jsonify, request, send_file
import json
from archive import list_runs, get_run, compare_runs
from pathlib import Path
import os

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

def format_time(seconds):
    """Format seconds into readable duration."""
    if seconds is None or seconds < 0:
        return "0.00s"
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:05.2f}s"

@app.route('/')
def index():
    """Home page: list recent runs."""
    runs = list_runs(limit=20)
    return render_template('index.html', runs=runs)

@app.route('/api/runs')
def api_runs():
    """API: get recent runs."""
    limit = request.args.get('limit', 20, type=int)
    server_filter = request.args.get('server_type', None)
    runs = list_runs(limit=limit, server_type_filter=server_filter)
    return jsonify(runs)

@app.route('/api/runs/<int:run_id>')
def api_run_detail(run_id):
    """API: get full run details."""
    run = get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    return jsonify(run)

@app.route('/api/compare/<int:run_1>/<int:run_2>')
def api_compare(run_1, run_2):
    """API: compare two runs."""
    comparison = compare_runs(run_1, run_2)
    if not comparison:
        return jsonify({"error": "Could not compare runs"}), 404
    return jsonify(comparison)

@app.route('/run/<int:run_id>')
def run_detail(run_id):
    """Detail page for a specific run."""
    run = get_run(run_id)
    if not run:
        return "Run not found", 404
    return render_template('run_detail.html', run=run)

@app.route('/compare')
def compare_page():
    """Comparison page: select two runs to compare."""
    runs = list_runs(limit=50)
    return render_template('compare.html', runs=runs)

@app.route('/trends')
def trends():
    """Trends page: show performance over time."""
    runs = list_runs(limit=50)
    return render_template('trends.html', runs=runs)

@app.route('/api/backup/<int:run_id>')
def download_backup(run_id):
    """Download JSON backup for a run."""
    # Find the JSON file closest to this run ID
    backup_dir = Path("benchmark_data")
    if not backup_dir.exists():
        return jsonify({"error": "Backup not found"}), 404
    
    files = list(backup_dir.glob("run_*.json"))
    if not files:
        return jsonify({"error": "No backups found"}), 404
    
    # Return the most recent one (this is a simplified approach)
    latest = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
    return send_file(latest, as_attachment=True)

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    Path('templates').mkdir(exist_ok=True)
    
    port = 8888
    print(f"Starting web app on http://localhost:{port}")
    print("Press Ctrl+C to stop")
    
    app.run(debug=False, host='localhost', port=port)

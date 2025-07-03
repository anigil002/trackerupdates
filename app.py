"""
Flask Application for Recruitment Tracker System
"""
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import json
import pandas as pd
from datetime import datetime
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database
from excel_manager import ExcelManager
from email_monitor import EmailMonitor
from ai_processor import AIProcessor

# Initialize Flask app
app = Flask(__name__)
CORS(app)



# Initialize components
db = Database()
excel_manager = ExcelManager()
ai_processor = AIProcessor(excel_manager=excel_manager)
email_monitor = EmailMonitor(ai_processor=ai_processor)

# Routes
@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html')

@app.route('/api/system/status')
def system_status():
    """Get system status"""
    return jsonify({
        'email_monitoring': email_monitor.monitoring,
        'ai_configured': ai_processor.model is not None,
        'pending_emails': email_monitor.email_queue.qsize(),
        'recent_activities': email_monitor.get_activities()[-5:]  # Last 5 activities
    })

@app.route('/api/system/start_monitoring', methods=['POST'])
def start_monitoring():
    """Start email monitoring"""
    success = email_monitor.start_monitoring()
    return jsonify({'success': success})

@app.route('/api/system/stop_monitoring', methods=['POST'])
def stop_monitoring():
    """Stop email monitoring"""
    success = email_monitor.stop_monitoring()
    return jsonify({'success': success})

@app.route('/api/email/activities')
def get_email_activities():
    """Get recent email monitoring activities"""
    activities = email_monitor.get_activities()
    return jsonify(activities)

@app.route('/api/config/ai_key', methods=['POST'])
def set_ai_key():
    """Set AI API key"""
    data = request.json
    api_key = data.get('api_key')
    
    if api_key:
        # Save to database
        db.set_config('ai_api_key', api_key, encrypt=True)
        
        # Initialize AI
        success = ai_processor.initialize_ai(api_key)
        
        return jsonify({'success': success})
    
    return jsonify({'success': False, 'error': 'No API key provided'})

@app.route('/api/hiring_managers', methods=['GET', 'POST'])
def hiring_managers():
    """Handle hiring managers"""
    if request.method == 'POST':
        data = request.json
        hm_id = db.add_hiring_manager(data['name'], data['email'])
        return jsonify({'success': hm_id is not None, 'id': hm_id})
    else:
        hms = db.get_hiring_managers()
        return jsonify([{
            'id': hm[0],
            'name': hm[1],
            'email': hm[2]
        } for hm in hms])

@app.route('/api/projects', methods=['GET', 'POST'])
def projects():
    """Handle projects"""
    if request.method == 'POST':
        data = request.json
        
        if isinstance(data, list):
            # Bulk add
            results = []
            for project_name in data:
                project_id = db.add_project(project_name)
                results.append({'name': project_name, 'id': project_id})
            return jsonify({'success': True, 'results': results})
        else:
            # Single add
            project_id = db.add_project(data['name'])
            return jsonify({'success': project_id is not None, 'id': project_id})
    else:
        projects = db.get_projects()
        return jsonify([{
            'id': proj[0],
            'name': proj[1]
        } for proj in projects])

@app.route('/api/jobs', methods=['GET', 'POST'])
def jobs():
    """Handle jobs"""
    if request.method == 'POST':
        data = request.json
        
        if isinstance(data, list):
            # Bulk add
            results = []
            for job in data:
                job_id, message = excel_manager.add_job(job)
                results.append({
                    'job': job.get('Job Title'),
                    'id': job_id,
                    'message': message
                })
            return jsonify({'success': True, 'results': results})
        else:
            # Single add
            job_id, message = excel_manager.add_job(data)
            return jsonify({
                'success': job_id is not None,
                'id': job_id,
                'message': message
            })
    else:
        df = excel_manager.read_master_tracker()
        return jsonify(df.to_dict('records'))

@app.route('/api/cvs', methods=['GET', 'POST'])
def cvs():
    """Handle CVs"""
    if request.method == 'POST':
        data = request.json
        cv_id, message = excel_manager.add_cv(data)
        return jsonify({
            'success': cv_id is not None,
            'id': cv_id,
            'message': message
        })
    else:
        df = excel_manager.read_cv_tracker()
        # Convert datetime objects to strings
        df = df.fillna('')
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]':
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(df.to_dict('records'))

@app.route('/api/jobs/<job_id>', methods=['PUT'])
def update_job(job_id):
    """Update job"""
    data = request.json
    success, message = excel_manager.update_job(job_id, data)
    return jsonify({'success': success, 'message': message})

@app.route('/api/cvs/<cv_id>', methods=['PUT'])
def update_cv(cv_id):
    """Update CV"""
    data = request.json
    success, message = excel_manager.update_cv(cv_id, data)
    return jsonify({'success': success, 'message': message})

@app.route('/api/ai/command', methods=['POST'])
def ai_command():
    """Process AI command"""
    data = request.json
    command = data.get('command')
    
    if not command:
        return jsonify({'error': 'No command provided'})
    
    result = ai_processor.process_command(command)
    return jsonify(result)

@app.route('/api/analytics/summary')
def analytics_summary():
    """Get analytics summary"""
    jobs_df = excel_manager.read_master_tracker()
    cvs_df = excel_manager.read_cv_tracker()
    
    summary = {
        'total_jobs': len(jobs_df),
        'open_jobs': len(jobs_df[jobs_df['Job Status'] == 'Open']) if not jobs_df.empty else 0,
        'filled_jobs': len(jobs_df[jobs_df['Job Status'] == 'Filled']) if not jobs_df.empty else 0,
        'total_cvs': len(cvs_df),
        'interviews_scheduled': len(cvs_df[cvs_df['Application Status'] == 'Interview Scheduled']) if not cvs_df.empty else 0,
        'offers_extended': len(cvs_df[cvs_df['Application Status'] == 'Offer Extended']) if not cvs_df.empty else 0,
        'hired': len(cvs_df[cvs_df['Application Status'] == 'Hired']) if not cvs_df.empty else 0
    }
    
    return jsonify(summary)

@app.route('/api/candidates', methods=['GET', 'POST'])
def candidates():
    """Handle candidates"""
    if request.method == 'POST':
        data = request.json
        candidate_id = db.add_candidate(
            name=data['name'],
            email=data.get('email', ''),
            mobile=data.get('mobile', ''),
            current_location=data.get('current_location', ''),
            nationality=data.get('nationality', ''),
            notice_period=data.get('notice_period', '')
        )
        return jsonify({'success': candidate_id is not None, 'id': candidate_id})
    else:
        candidates = db.get_candidates()
        return jsonify([{
            'id': c[0],
            'name': c[1],
            'email': c[2],
            'mobile': c[3],
            'current_location': c[4],
            'nationality': c[5],
            'notice_period': c[6]
        } for c in candidates])

@app.route('/api/candidates/bulk', methods=['POST'])
def bulk_add_candidates():
    """Bulk add candidates"""
    candidates_data = request.json
    results = []
    
    for candidate in candidates_data:
        try:
            candidate_id = db.add_candidate(
                name=candidate['name'],
                email=candidate.get('email', ''),
                mobile=candidate.get('mobile', ''),
                current_location=candidate.get('current_location', ''),
                nationality=candidate.get('nationality', ''),
                notice_period=candidate.get('notice_period', '')
            )
            results.append({
                'name': candidate['name'],
                'success': candidate_id is not None,
                'id': candidate_id
            })
        except Exception as e:
            results.append({
                'name': candidate['name'],
                'success': False,
                'error': str(e)
            })
    
    success_count = sum(1 for r in results if r['success'])
    return jsonify({
        'success': True,
        'results': results,
        'summary': {
            'total': len(results),
            'success': success_count,
            'failed': len(results) - success_count
        }
    })

@app.route('/api/export/<tracker_type>')
def export_tracker(tracker_type):
    """Export tracker data"""
    if tracker_type == 'master':
        # Get the absolute path to the Excel file
        file_path = Path(excel_manager.master_path).absolute()
        
        # Check if file exists
        if not file_path.exists():
            return jsonify({'error': 'Master Tracker file not found. Please add some jobs first.'}), 404
            
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=f'MasterTracker_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    elif tracker_type == 'cv':
        # Get the absolute path to the Excel file
        file_path = Path(excel_manager.cv_path).absolute()
        
        # Check if file exists
        if not file_path.exists():
            return jsonify({'error': 'CV Tracker file not found. Please add some CVs first.'}), 404
            
        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=f'CVTracker_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    else:
        return jsonify({'error': 'Invalid tracker type'}), 400

if __name__ == '__main__':
    # Check if AI key exists
    api_key = db.get_config('ai_api_key', decrypt=True)
    if api_key:
        ai_processor.initialize_ai(api_key)
    
    # Run Flask app
    app.run(debug=True, port=5000)
"""
AI Processor for Email Analysis and Natural Language Commands
"""
import google.generativeai as genai
import json
import re
from datetime import datetime, timedelta
from dateutil import parser

class AIProcessor:
    def __init__(self, api_key=None, excel_manager=None):
        self.api_key = api_key
        self.excel_manager = excel_manager
        self.model = None
        if api_key:
            self.initialize_ai(api_key)
    
    def initialize_ai(self, api_key):
        """Initialize Gemini AI"""
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
            self.api_key = api_key
            return True
        except Exception as e:
            print(f"Failed to initialize AI: {e}")
            return False
    
    def process_email(self, email_data):
        """Process email with AI to extract recruitment information"""
        if not self.model:
            return None
        
        prompt = f"""
        Analyze this recruitment email and extract relevant information:
        
        Subject: {email_data['subject']}
        From: {email_data['sender']}
        Body: {email_data['body'][:2000]}
        
        Extract the following if present:
        1. Candidate name(s)
        2. Position/Job title
        3. Project name
        4. CV submission details
        5. Interview schedule information
        6. Hiring manager feedback
        7. Offer details
        8. Any status updates
        
        Return as JSON format with appropriate fields.
        """
        
        try:
            response = self.model.generate_content(prompt)
            extracted_data = self._parse_ai_response(response.text)
            
            # Process extracted data
            self._update_trackers(extracted_data, email_data)
            
            return extracted_data
        except Exception as e:
            print(f"AI processing error: {e}")
            return None
    
    def process_command(self, command):
        """Process natural language command"""
        if not self.model:
            return {"error": "AI not initialized", "response": "Please configure AI API key first."}
        
        prompt = f"""
        Parse this recruitment system command and extract the action and parameters:
        
        Command: {command}
        
        Possible actions:
        1. Add/Log candidate(s) - Extract: candidate names, job ID, CV source, email, etc.
        2. Update CV/candidate status - Extract: CV ID, new status, dates, comments
        3. Add hiring manager - Extract: name, email, project
        4. Add project - Extract: project name
        5. Search/Show data - Extract: search criteria, filters
        6. Send email - Extract: recipient, subject, content
        
        Return as JSON with 'action' and 'parameters' fields.
        """
        
        try:
            response = self.model.generate_content(prompt)
            parsed_command = self._parse_ai_response(response.text)
            
            # Execute command
            result = self._execute_command(parsed_command)
            
            return result
        except Exception as e:
            return {"error": str(e), "response": "Failed to process command."}
    
    def _parse_ai_response(self, response_text):
        """Parse AI response to extract JSON"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Try to parse the entire response
                return json.loads(response_text)
        except:
            # Return empty dict if parsing fails
            return {}
    
    def _update_trackers(self, extracted_data, email_data):
        """Update Excel trackers based on extracted data"""
        if not self.excel_manager:
            return
        
        try:
            # Check if it's a CV submission
            if extracted_data.get('candidate_name') and extracted_data.get('position'):
                cv_data = {
                    'Candidate Name': extracted_data['candidate_name'],
                    'Position': extracted_data['position'],
                    'CV Source': extracted_data.get('cv_source', 'Email'),
                    'Date CV Shared': datetime.now().date(),
                    'Email': extracted_data.get('email', ''),
                    'Application Status': 'CV Shared'
                }
                
                # Try to find matching JobID
                if extracted_data.get('job_id'):
                    cv_data['JobID'] = extracted_data['job_id']
                else:
                    # Search for matching job
                    jobs = self.excel_manager.search_jobs({
                        'Job Title': extracted_data['position']
                    })
                    if not jobs.empty:
                        cv_data['JobID'] = jobs.iloc[0]['JobID']
                
                if cv_data.get('JobID'):
                    self.excel_manager.add_cv(cv_data)
            
            # Check if it's interview scheduling
            if extracted_data.get('interview_date') and extracted_data.get('candidate_name'):
                # Find CV record
                cvs = self.excel_manager.search_cvs({
                    'Candidate Name': extracted_data['candidate_name']
                })
                if not cvs.empty:
                    cv_id = cvs.iloc[0]['CVID']
                    self.excel_manager.update_cv(cv_id, {
                        'Interview Date': extracted_data['interview_date'],
                        'Application Status': 'Interview Scheduled'
                    })
            
            # Check if it's feedback
            if extracted_data.get('feedback') and extracted_data.get('candidate_name'):
                cvs = self.excel_manager.search_cvs({
                    'Candidate Name': extracted_data['candidate_name']
                })
                if not cvs.empty:
                    cv_id = cvs.iloc[0]['CVID']
                    self.excel_manager.update_cv(cv_id, {
                        'HM Feedback': extracted_data['feedback'],
                        'HM Feedback Date': datetime.now().date()
                    })
                    
        except Exception as e:
            print(f"Error updating trackers: {e}")
    
    def _execute_command(self, parsed_command):
        """Execute parsed command"""
        action = parsed_command.get('action', '').lower()
        params = parsed_command.get('parameters', {})
        
        try:
            if 'add' in action and 'candidate' in action:
                return self._add_candidates(params)
            elif 'update' in action:
                return self._update_status(params)
            elif 'add' in action and 'manager' in action:
                return self._add_hiring_manager(params)
            elif 'add' in action and 'project' in action:
                return self._add_project(params)
            elif 'search' in action or 'show' in action:
                return self._search_data(params)
            else:
                return {"response": "Command understood but not yet implemented."}
                
        except Exception as e:
            return {"error": str(e), "response": "Failed to execute command."}
    
    def _add_candidates(self, params):
        """Add candidates to CV tracker"""
        if not self.excel_manager:
            return {"error": "Excel manager not available"}
        
        candidates = params.get('candidates', [])
        job_id = params.get('job_id')
        
        if not candidates:
            return {"response": "No candidates found in command."}
        
        results = []
        for candidate in candidates:
            cv_data = {
                'JobID': job_id,
                'Candidate Name': candidate.get('name'),
                'CV Source': candidate.get('source', 'Direct'),
                'Email': candidate.get('email', ''),
                'Application Status': 'CV Shared',
                'Date CV Shared': datetime.now().date()
            }
            
            cv_id, message = self.excel_manager.add_cv(cv_data)
            if cv_id:
                results.append(f"Added {candidate.get('name')} (ID: {cv_id})")
            else:
                results.append(f"Failed to add {candidate.get('name')}: {message}")
        
        return {"response": "\n".join(results)}
    
    def _update_status(self, params):
        """Update CV status"""
        if not self.excel_manager:
            return {"error": "Excel manager not available"}
        
        cv_id = params.get('cv_id')
        updates = params.get('updates', {})
        
        if not cv_id:
            return {"response": "CV ID not specified."}
        
        success, message = self.excel_manager.update_cv(cv_id, updates)
        
        return {"response": message}
    
    def _add_hiring_manager(self, params):
        """Add hiring manager"""
        # This would integrate with the database module
        return {"response": f"Hiring manager {params.get('name')} would be added."}
    
    def _add_project(self, params):
        """Add project"""
        # This would integrate with the database module
        return {"response": f"Project {params.get('name')} would be added."}
    
    def _search_data(self, params):
        """Search tracker data"""
        if not self.excel_manager:
            return {"error": "Excel manager not available"}
        
        search_type = params.get('type', 'cv')
        criteria = params.get('criteria', {})
        
        if search_type == 'job':
            results = self.excel_manager.search_jobs(criteria)
        else:
            results = self.excel_manager.search_cvs(criteria)
        
        if results.empty:
            return {"response": "No results found."}
        
        # Format results
        response = f"Found {len(results)} results:\n"
        for _, row in results.head(10).iterrows():
            if search_type == 'job':
                response += f"- {row['JobID']}: {row['Job Title']} ({row['Job Status']})\n"
            else:
                response += f"- {row['CVID']}: {row['Candidate Name']} ({row['Application Status']})\n"
        
        return {"response": response, "data": results.to_dict('records')}

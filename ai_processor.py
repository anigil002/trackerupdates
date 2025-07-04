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
        From: {email_data['sender_name']} ({email_data['sender']})
        Body: {email_data['body'][:2000]}
        Attachments: {', '.join([att['filename'] for att in email_data.get('attachments', [])])}
        
        Extract the following if present:
        1. Candidate name(s)
        2. Position/Job title
        3. Project name
        4. CV submission details
        5. Interview schedule information (date, time, location)
        6. Hiring manager feedback
        7. Interview results
        8. Offer details
        9. Any status updates
        10. Email address of candidate
        11. Phone number
        12. Current location
        13. Notice period
        14. Nationality
        
        Return as JSON format with appropriate fields. Use these field names:
        - candidate_name
        - position
        - project_name
        - job_id (if mentioned)
        - cv_source
        - email
        - mobile
        - current_location
        - notice_period
        - nationality
        - interview_date
        - interview_time
        - interview_location
        - feedback
        - interview_result
        - offer_details
        - status_update
        """
        
        try:
            response = self.model.generate_content(prompt)
            extracted_data = self._parse_ai_response(response.text)
            
            # Process extracted data and update trackers
            result = self._update_trackers(extracted_data, email_data)
            
            return result
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
        1. Add/Log candidate(s) - Extract: candidate names, job ID, CV source, email, mobile, location, etc.
        2. Update CV/candidate status - Extract: CV ID, new status, dates, comments
        3. Add hiring manager - Extract: name, email, project
        4. Add project - Extract: project name
        5. Search/Show data - Extract: search criteria, filters
        6. Send email - Extract: recipient, subject, content
        7. Schedule interview - Extract: candidate, date, time, interviewer
        8. Update feedback - Extract: candidate, feedback, decision
        
        Return as JSON with 'action' and 'parameters' fields.
        For candidates, use array format in parameters.candidates
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
            return None
        
        action_taken = None
        
        try:
            # Check if it's a CV submission
            if extracted_data.get('candidate_name') and extracted_data.get('position'):
                cv_data = {
                    'Candidate Name': extracted_data['candidate_name'],
                    'Position': extracted_data['position'],
                    'CV Source': extracted_data.get('cv_source', 'Email'),
                    'Date CV Shared': datetime.now().date(),
                    'Email': extracted_data.get('email', ''),
                    'Mobile': extracted_data.get('mobile', ''),
                    'Current Location': extracted_data.get('current_location', ''),
                    'Notice Period': extracted_data.get('notice_period', ''),
                    'Nationality': extracted_data.get('nationality', ''),
                    'Application Status': 'CV Shared'
                }
                
                # Add project if specified
                if extracted_data.get('project_name'):
                    cv_data['Project'] = extracted_data['project_name']
                
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
                        # Get project from job if not already set
                        if not cv_data.get('Project'):
                            cv_data['Project'] = jobs.iloc[0].get('Project Name', '')
                
                if cv_data.get('JobID'):
                    cv_id, message = self.excel_manager.add_cv(cv_data)
                    if cv_id:
                        action_taken = f"Added CV for {extracted_data['candidate_name']} (ID: {cv_id})"
                        extracted_data['action_taken'] = action_taken
            
            # Check if it's interview scheduling
            if extracted_data.get('interview_date') and extracted_data.get('candidate_name'):
                # Find CV record
                cvs = self.excel_manager.search_cvs({
                    'Candidate Name': extracted_data['candidate_name']
                })
                if not cvs.empty:
                    cv_id = cvs.iloc[0]['CVID']
                    
                    # Parse interview date
                    try:
                        interview_datetime = parser.parse(extracted_data['interview_date'])
                        if extracted_data.get('interview_time'):
                            # Combine date and time if separate
                            time_str = extracted_data['interview_time']
                            interview_datetime = parser.parse(f"{extracted_data['interview_date']} {time_str}")
                    except:
                        interview_datetime = extracted_data['interview_date']
                    
                    updates = {
                        'Interview Date': interview_datetime,
                        'Application Status': 'Interview Scheduled'
                    }
                    
                    if extracted_data.get('interview_location'):
                        updates['Remarks'] = f"Interview Location: {extracted_data['interview_location']}"
                    
                    success, message = self.excel_manager.update_cv(cv_id, updates)
                    if success:
                        action_taken = f"Updated interview schedule for {extracted_data['candidate_name']}"
                        extracted_data['action_taken'] = action_taken
            
            # Check if it's feedback or interview results
            if (extracted_data.get('feedback') or extracted_data.get('interview_result')) and extracted_data.get('candidate_name'):
                cvs = self.excel_manager.search_cvs({
                    'Candidate Name': extracted_data['candidate_name']
                })
                if not cvs.empty:
                    cv_id = cvs.iloc[0]['CVID']
                    updates = {}
                    
                    if extracted_data.get('feedback'):
                        updates['HM Feedback'] = extracted_data['feedback']
                        updates['HM Feedback Date'] = datetime.now().date()
                        
                        # Add to comments if long feedback
                        if len(extracted_data['feedback']) > 100:
                            updates['HM Comments'] = extracted_data['feedback']
                            updates['HM Feedback'] = extracted_data['feedback'][:100] + "..."
                    
                    if extracted_data.get('interview_result'):
                        updates['Interview Results'] = extracted_data['interview_result']
                        updates['Date Interview Result'] = datetime.now().date()
                        
                        # Update status based on result
                        result_lower = extracted_data['interview_result'].lower()
                        if any(word in result_lower for word in ['pass', 'selected', 'yes', 'approved']):
                            updates['Application Status'] = 'Interview Passed'
                        elif any(word in result_lower for word in ['fail', 'reject', 'no']):
                            updates['Application Status'] = 'Rejected'
                    
                    success, message = self.excel_manager.update_cv(cv_id, updates)
                    if success:
                        action_taken = f"Updated feedback for {extracted_data['candidate_name']}"
                        extracted_data['action_taken'] = action_taken
            
            # Check if it's an offer
            if extracted_data.get('offer_details') and extracted_data.get('candidate_name'):
                cvs = self.excel_manager.search_cvs({
                    'Candidate Name': extracted_data['candidate_name']
                })
                if not cvs.empty:
                    cv_id = cvs.iloc[0]['CVID']
                    updates = {
                        'Application Status': 'Offer Extended',
                        'Date Offer Issued': datetime.now().date(),
                        'Offer Status': 'Pending'
                    }
                    
                    # Extract salary if mentioned
                    salary_match = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:AED|USD|GBP|EUR)?', extracted_data['offer_details'])
                    if salary_match:
                        updates['Package'] = salary_match.group(1).replace(',', '')
                    
                    success, message = self.excel_manager.update_cv(cv_id, updates)
                    if success:
                        action_taken = f"Updated offer details for {extracted_data['candidate_name']}"
                        extracted_data['action_taken'] = action_taken
                    
        except Exception as e:
            print(f"Error updating trackers: {e}")
        
        return extracted_data
    
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
            elif 'schedule' in action and 'interview' in action:
                return self._schedule_interview(params)
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
        
        # Handle single candidate as well
        if not candidates and params.get('name'):
            candidates = [{
                'name': params.get('name'),
                'email': params.get('email'),
                'source': params.get('source', 'Direct')
            }]
        
        if not candidates:
            return {"response": "No candidates found in command."}
        
        results = []
        for candidate in candidates:
            cv_data = {
                'JobID': job_id,
                'Candidate Name': candidate.get('name'),
                'CV Source': candidate.get('source', 'Direct'),
                'Email': candidate.get('email', ''),
                'Mobile': candidate.get('mobile', ''),
                'Current Location': candidate.get('location', ''),
                'Application Status': 'CV Shared',
                'Date CV Shared': datetime.now().date()
            }
            
            cv_id, message = self.excel_manager.add_cv(cv_data)
            if cv_id:
                results.append(f"✓ Added {candidate.get('name')} (ID: {cv_id})")
            else:
                results.append(f"✗ Failed to add {candidate.get('name')}: {message}")
        
        return {"response": "\n".join(results)}
    
    def _update_status(self, params):
        """Update CV status"""
        if not self.excel_manager:
            return {"error": "Excel manager not available"}
        
        cv_id = params.get('cv_id')
        updates = params.get('updates', {})
        
        # Map common status updates
        if params.get('status'):
            updates['Application Status'] = params['status']
        if params.get('interview_date'):
            updates['Interview Date'] = params['interview_date']
        if params.get('feedback'):
            updates['HM Feedback'] = params['feedback']
            updates['HM Feedback Date'] = datetime.now().date()
        
        if not cv_id:
            return {"response": "CV ID not specified."}
        
        success, message = self.excel_manager.update_cv(cv_id, updates)
        
        return {"response": message}
    
    def _schedule_interview(self, params):
        """Schedule interview for candidate"""
        if not self.excel_manager:
            return {"error": "Excel manager not available"}
        
        candidate_name = params.get('candidate')
        interview_date = params.get('date')
        interview_time = params.get('time')
        interviewer = params.get('interviewer')
        
        if not candidate_name:
            return {"response": "Candidate name not specified."}
        
        # Find candidate
        cvs = self.excel_manager.search_cvs({
            'Candidate Name': candidate_name
        })
        
        if cvs.empty:
            return {"response": f"Candidate {candidate_name} not found."}
        
        cv_id = cvs.iloc[0]['CVID']
        
        # Combine date and time
        interview_datetime = interview_date
        if interview_time:
            interview_datetime = f"{interview_date} {interview_time}"
        
        updates = {
            'Interview Date': interview_datetime,
            'Application Status': 'Interview Scheduled'
        }
        
        if interviewer:
            updates['Remarks'] = f"Interview with {interviewer}"
        
        success, message = self.excel_manager.update_cv(cv_id, updates)
        
        if success:
            return {"response": f"Interview scheduled for {candidate_name} on {interview_datetime}"}
        else:
            return {"response": f"Failed to schedule interview: {message}"}
    
    def _add_hiring_manager(self, params):
        """Add hiring manager"""
        # This would integrate with the database module
        return {"response": f"Hiring manager {params.get('name')} would be added with email {params.get('email')}."}
    
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
        
        # Handle various search patterns
        if params.get('project'):
            criteria['Project'] = params['project']
        if params.get('position'):
            criteria['Position'] = params['position']
        if params.get('status'):
            criteria['Application Status'] = params['status']
        if params.get('candidate'):
            criteria['Candidate Name'] = params['candidate']
        
        if search_type == 'job':
            results = self.excel_manager.search_jobs(criteria)
        else:
            results = self.excel_manager.search_cvs(criteria)
        
        if results.empty:
            return {"response": "No results found."}
        
        # Format results
        response = f"Found {len(results)} results:\n\n"
        for idx, row in results.head(10).iterrows():
            if search_type == 'job':
                response += f"• {row['JobID']}: {row['Job Title']} at {row['Project Name']} ({row['Job Status']})\n"
            else:
                response += f"• {row['CVID']}: {row['Candidate Name']} for {row['Position']} ({row['Application Status']})\n"
                if row.get('Interview Date'):
                    response += f"  Interview: {row['Interview Date']}\n"
        
        if len(results) > 10:
            response += f"\n... and {len(results) - 10} more results"
        
        return {"response": response, "data": results.to_dict('records')}
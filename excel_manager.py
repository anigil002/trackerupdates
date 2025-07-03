"""
Excel Manager for Recruitment Tracker System
"""
import pandas as pd
from datetime import datetime
from pathlib import Path
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows

class ExcelManager:
    def __init__(self, master_path="data/MasterTracker.xlsx", cv_path="data/CVTracker.xlsx"):
        self.master_path = Path(master_path)
        self.cv_path = Path(cv_path)
        self.init_excel_files()
    
    def init_excel_files(self):
        """Initialize Excel files if they don't exist"""
        # Master Tracker columns
        master_columns = [
            "JobID", "Position Created Date", "Job Title", "Job Location (Country)",
            "Project Name", "Max Budgeted Salary", "Accepted Salary", "Is Job Ad Published?",
            "TA Partner", "Sourcing Partner", "Hiring Manager", "Job Status",
            "Business Line", "Service Line"
        ]
        
        # CV Tracker columns
        cv_columns = [
            "CVID", "JobID", "Position", "Hiring Manager", "Project", "Candidate Name",
            "Application Status", "CV Source", "Date CV Shared", "HM Feedback",
            "HM Feedback Date", "HM Comments", "Interview Date", "Interview Results",
            "Date Interview Result", "Package", "Date Offer Requested", "Date Offer Issued",
            "Offer Status", "Date Offer Accepted or Rejected", "Remarks", "ETA",
            "Date Onboard", "Email", "Mobile", "Current Location", "Notice Period",
            "Agreed Start Date", "Nationality", "Last Modified"
        ]
        
        # Create Master Tracker if not exists
        if not self.master_path.exists():
            df = pd.DataFrame(columns=master_columns)
            self.save_with_formatting(df, self.master_path, "Master Tracker")
        
        # Create CV Tracker if not exists
        if not self.cv_path.exists():
            df = pd.DataFrame(columns=cv_columns)
            self.save_with_formatting(df, self.cv_path, "CV Tracker")
    
    def save_with_formatting(self, df, path, sheet_name):
        """Save DataFrame with formatting"""
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]
            
            # Format headers
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            
            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    def generate_job_id(self):
        """Generate unique JobID"""
        df = self.read_master_tracker()
        date_part = datetime.now().strftime("%y%m%d")
        prefix = f"JOB-{date_part}"
        
        # Find existing IDs for today
        existing = df[df['JobID'].str.startswith(prefix)] if not df.empty else pd.DataFrame()
        
        if existing.empty:
            return f"{prefix}-001"
        else:
            # Extract numbers and find max
            numbers = existing['JobID'].str.extract(r'(\d{3})$')[0].astype(int)
            next_num = numbers.max() + 1
            return f"{prefix}-{next_num:03d}"
    
    def generate_cv_id(self):
        """Generate unique CVID"""
        df = self.read_cv_tracker()
        date_part = datetime.now().strftime("%y%m%d")
        prefix = f"CV-{date_part}"
        
        # Find existing IDs for today
        existing = df[df['CVID'].str.startswith(prefix)] if not df.empty else pd.DataFrame()
        
        if existing.empty:
            return f"{prefix}-001"
        else:
            # Extract numbers and find max
            numbers = existing['CVID'].str.extract(r'(\d{3})$')[0].astype(int)
            next_num = numbers.max() + 1
            return f"{prefix}-{next_num:03d}"
    
    def read_master_tracker(self):
        """Read Master Tracker"""
        try:
            return pd.read_excel(self.master_path, sheet_name="Master Tracker")
        except:
            return pd.DataFrame()
    
    def read_cv_tracker(self):
        """Read CV Tracker"""
        try:
            return pd.read_excel(self.cv_path, sheet_name="CV Tracker")
        except:
            return pd.DataFrame()
    
    def add_job(self, job_data):
        """Add new job to Master Tracker"""
        df = self.read_master_tracker()
        
        # Check for duplicates
        if not df.empty:
            duplicate = df[
                (df['Job Title'] == job_data.get('Job Title')) &
                (df['Project Name'] == job_data.get('Project Name')) &
                (df['Job Location (Country)'] == job_data.get('Job Location (Country)'))
            ]
            if not duplicate.empty:
                return None, "Duplicate job found"
        
        # Generate JobID if not provided
        if 'JobID' not in job_data or not job_data['JobID']:
            job_data['JobID'] = self.generate_job_id()
        
        # Add default values
        if 'Position Created Date' not in job_data:
            job_data['Position Created Date'] = datetime.now().date()
        
        # Append to dataframe
        df = pd.concat([df, pd.DataFrame([job_data])], ignore_index=True)
        self.save_with_formatting(df, self.master_path, "Master Tracker")
        
        return job_data['JobID'], "Job added successfully"
    
    def add_cv(self, cv_data):
        """Add new CV to CV Tracker"""
        df = self.read_cv_tracker()
        
        # Generate CVID if not provided
        if 'CVID' not in cv_data or not cv_data['CVID']:
            cv_data['CVID'] = self.generate_cv_id()
        
        # Validate JobID exists
        master_df = self.read_master_tracker()
        if cv_data.get('JobID') not in master_df['JobID'].values:
            return None, "Invalid JobID"
        
        # Auto-populate from Master Tracker
        job_info = master_df[master_df['JobID'] == cv_data['JobID']].iloc[0]
        cv_data['Position'] = cv_data.get('Position', job_info['Job Title'])
        cv_data['Hiring Manager'] = cv_data.get('Hiring Manager', job_info['Hiring Manager'])
        cv_data['Project'] = cv_data.get('Project', job_info['Project Name'])
        
        # Add timestamp
        cv_data['Last Modified'] = datetime.now()
        
        # Append to dataframe
        df = pd.concat([df, pd.DataFrame([cv_data])], ignore_index=True)
        self.save_with_formatting(df, self.cv_path, "CV Tracker")
        
        return cv_data['CVID'], "CV added successfully"
    
    def update_job(self, job_id, updates):
        """Update job in Master Tracker"""
        df = self.read_master_tracker()
        
        if job_id not in df['JobID'].values:
            return False, "Job not found"
        
        for key, value in updates.items():
            df.loc[df['JobID'] == job_id, key] = value
        
        self.save_with_formatting(df, self.master_path, "Master Tracker")
        return True, "Job updated successfully"
    
    def update_cv(self, cv_id, updates):
        """Update CV in CV Tracker"""
        df = self.read_cv_tracker()
        
        if cv_id not in df['CVID'].values:
            return False, "CV not found"
        
        updates['Last Modified'] = datetime.now()
        
        for key, value in updates.items():
            df.loc[df['CVID'] == cv_id, key] = value
        
        self.save_with_formatting(df, self.cv_path, "CV Tracker")
        
        # Check if status changed to "Hired" to update Master Tracker
        if updates.get('Application Status') == 'Hired':
            job_id = df.loc[df['CVID'] == cv_id, 'JobID'].iloc[0]
            self.update_job(job_id, {'Job Status': 'Filled'})
        
        return True, "CV updated successfully"
    
    def search_jobs(self, criteria):
        """Search jobs based on criteria"""
        df = self.read_master_tracker()
        
        for key, value in criteria.items():
            if key in df.columns and value:
                df = df[df[key].str.contains(value, case=False, na=False)]
        
        return df
    
    def search_cvs(self, criteria):
        """Search CVs based on criteria"""
        df = self.read_cv_tracker()
        
        for key, value in criteria.items():
            if key in df.columns and value:
                df = df[df[key].str.contains(value, case=False, na=False)]
        
        return df

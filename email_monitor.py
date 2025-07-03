"""
Email Monitor for Outlook Integration with Activity Tracking
"""
import win32com.client
import pythoncom
import threading
import queue
import time
from datetime import datetime
import re

class EmailMonitor:
    def __init__(self, ai_processor=None):
        self.ai_processor = ai_processor
        self.monitoring = False
        self.email_queue = queue.Queue()
        self.monitor_thread = None
        self.activity_log = []  # Store email activity
        self.max_activities = 50  # Keep last 50 activities
        
    def start_monitoring(self):
        """Start email monitoring"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_emails)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            self.add_activity("system", "Email monitoring started")
            return True
        return False
    
    def stop_monitoring(self):
        """Stop email monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.add_activity("system", "Email monitoring stopped")
        return True
    
    def add_activity(self, activity_type, message, email_subject=None):
        """Add activity to the log"""
        activity = {
            'timestamp': datetime.now().isoformat(),
            'type': activity_type,
            'message': message,
            'subject': email_subject
        }
        
        self.activity_log.append(activity)
        
        # Keep only last N activities
        if len(self.activity_log) > self.max_activities:
            self.activity_log = self.activity_log[-self.max_activities:]
    
    def get_activities(self):
        """Get recent activities"""
        return self.activity_log[-20:]  # Return last 20 activities
    
    def _monitor_emails(self):
        """Monitor emails in background thread"""
        pythoncom.CoInitialize()
        
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            
            # Monitor Inbox
            inbox = namespace.GetDefaultFolder(6)  # 6 = Inbox
            sent = namespace.GetDefaultFolder(5)   # 5 = Sent Items
            
            self.add_activity("system", "Connected to Outlook successfully")
            
            # Get initial message counts
            inbox_count = inbox.Items.Count
            sent_count = sent.Items.Count
            
            self.add_activity("system", f"Monitoring started - Inbox: {inbox_count} emails, Sent: {sent_count} emails")
            
            while self.monitoring:
                try:
                    # Check for new emails in Inbox
                    current_inbox_count = inbox.Items.Count
                    if current_inbox_count > inbox_count:
                        # Process new emails
                        for i in range(inbox_count + 1, current_inbox_count + 1):
                            try:
                                message = inbox.Items[i]
                                self.add_activity("inbox", f"New email received", message.Subject)
                                self._process_email(message, "Inbox")
                            except Exception as e:
                                self.add_activity("error", f"Error processing inbox email: {str(e)}")
                        inbox_count = current_inbox_count
                    
                    # Check for new emails in Sent Items
                    current_sent_count = sent.Items.Count
                    if current_sent_count > sent_count:
                        # Process new emails
                        for i in range(sent_count + 1, current_sent_count + 1):
                            try:
                                message = sent.Items[i]
                                self.add_activity("sent", f"New email sent", message.Subject)
                                self._process_email(message, "Sent")
                            except Exception as e:
                                self.add_activity("error", f"Error processing sent email: {str(e)}")
                        sent_count = current_sent_count
                    
                    time.sleep(5)  # Check every 5 seconds
                    
                except Exception as e:
                    self.add_activity("error", f"Monitoring error: {str(e)}")
                    time.sleep(10)
                    
        except Exception as e:
            self.add_activity("error", f"Failed to connect to Outlook: {str(e)}")
        finally:
            pythoncom.CoUninitialize()
    
    def _process_email(self, message, folder):
        """Process individual email"""
        try:
            email_data = {
                'folder': folder,
                'subject': message.Subject,
                'sender': message.SenderEmailAddress,
                'recipients': self._get_recipients(message),
                'body': message.Body,
                'received_time': message.ReceivedTime,
                'attachments': self._get_attachments(message)
            }
            
            # Check if recruitment related
            if self._is_recruitment_email(email_data):
                self.email_queue.put(email_data)
                self.add_activity("recruitment", f"Recruitment email detected", email_data['subject'])
                
                # Process with AI if processor available
                if self.ai_processor:
                    self.add_activity("ai", f"Processing with AI", email_data['subject'])
                    result = self.ai_processor.process_email(email_data)
                    if result:
                        self.add_activity("ai", f"AI processing completed", email_data['subject'])
            else:
                self.add_activity("skip", f"Non-recruitment email skipped", email_data['subject'])
                    
        except Exception as e:
            self.add_activity("error", f"Error processing email: {str(e)}")
    
    def _get_recipients(self, message):
        """Extract email recipients"""
        recipients = []
        try:
            for recipient in message.Recipients:
                recipients.append({
                    'name': recipient.Name,
                    'email': recipient.Address
                })
        except:
            pass
        return recipients
    
    def _get_attachments(self, message):
        """Extract attachment information"""
        attachments = []
        try:
            for attachment in message.Attachments:
                attachments.append({
                    'filename': attachment.FileName,
                    'size': attachment.Size
                })
        except:
            pass
        return attachments
    
    def _is_recruitment_email(self, email_data):
        """Check if email is recruitment related"""
        keywords = [
            'cv', 'resume', 'candidate', 'interview', 'recruitment',
            'hiring', 'job', 'position', 'application', 'offer',
            'feedback', 'shortlist', 'profile', 'vacancy'
        ]
        
        text = f"{email_data['subject']} {email_data['body']}".lower()
        
        return any(keyword in text for keyword in keywords)
    
    def get_pending_emails(self):
        """Get pending emails from queue"""
        emails = []
        while not self.email_queue.empty():
            try:
                emails.append(self.email_queue.get_nowait())
            except:
                break
        return emails
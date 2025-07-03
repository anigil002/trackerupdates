// AI-Powered Recruitment Tracker - Complete Frontend JavaScript

// Global variables
let currentTab = 'dashboard';
let systemStatus = {
    monitoring: false,
    aiConfigured: false
};
let activityRefreshInterval = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing app...');
    initializeApp();
});

// Initialize application
async function initializeApp() {
    setupEventListeners();
    await loadSystemStatus();
    await loadDashboardData();
    await loadConfiguration();
    startActivityRefresh();
}

// Set up event listeners
function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    // Tab navigation
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            switchTab(this.dataset.tab);
        });
    });
    
    // System controls
    const startBtn = document.getElementById('btnStartMonitoring');
    const stopBtn = document.getElementById('btnStopMonitoring');
    
    if (startBtn) {
        startBtn.addEventListener('click', startMonitoring);
    }
    if (stopBtn) {
        stopBtn.addEventListener('click', stopMonitoring);
    }
    
    // AI command input
    const aiCommand = document.getElementById('aiCommand');
    if (aiCommand) {
        aiCommand.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendAICommand();
            }
        });
    }
    
    // Form submissions
    const addJobForm = document.getElementById('addJobForm');
    const addCVForm = document.getElementById('addCVForm');
    const addCandidateForm = document.getElementById('addCandidateForm');
    
    if (addJobForm) {
        addJobForm.addEventListener('submit', handleAddJob);
    }
    if (addCVForm) {
        addCVForm.addEventListener('submit', handleAddCV);
    }
    if (addCandidateForm) {
        addCandidateForm.addEventListener('submit', handleAddCandidate);
    }
}

// Tab switching
function switchTab(tabName) {
    console.log('Switching to tab:', tabName);
    
    // Update active tab
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(tabName).classList.add('active');
    
    currentTab = tabName;
    
    // Manage activity refresh
    if (tabName === 'dashboard') {
        startActivityRefresh();
    } else {
        stopActivityRefresh();
    }
    
    // Load tab-specific data
    switch(tabName) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'jobs':
            loadJobs();
            break;
        case 'cvs':
            loadCVs();
            break;
        case 'configuration':
            loadConfiguration();
            break;
    }
}

// System status functions
async function loadSystemStatus() {
    try {
        const response = await fetch('/api/system/status');
        const data = await response.json();
        
        systemStatus = data;
        updateSystemStatusUI();
    } catch (error) {
        console.error('Error loading system status:', error);
    }
}

function updateSystemStatusUI() {
    const statusElement = document.getElementById('monitoringStatus');
    const startBtn = document.getElementById('btnStartMonitoring');
    const stopBtn = document.getElementById('btnStopMonitoring');
    
    if (systemStatus.email_monitoring) {
        statusElement.textContent = 'Monitoring Active';
        statusElement.classList.add('monitoring');
        startBtn.style.display = 'none';
        stopBtn.style.display = 'inline-block';
    } else {
        statusElement.textContent = 'Not Monitoring';
        statusElement.classList.remove('monitoring');
        startBtn.style.display = 'inline-block';
        stopBtn.style.display = 'none';
    }
}

async function startMonitoring() {
    console.log('Starting monitoring...');
    try {
        const response = await fetch('/api/system/start_monitoring', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            showAlert('Email monitoring started', 'success');
            await loadSystemStatus();
        } else {
            showAlert('Failed to start monitoring', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error starting monitoring', 'error');
    }
}

async function stopMonitoring() {
    console.log('Stopping monitoring...');
    try {
        const response = await fetch('/api/system/stop_monitoring', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            showAlert('Email monitoring stopped', 'success');
            await loadSystemStatus();
        } else {
            showAlert('Failed to stop monitoring', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error stopping monitoring', 'error');
    }
}

// Email activity functions
function startActivityRefresh() {
    if (currentTab === 'dashboard' && !activityRefreshInterval) {
        refreshEmailActivities();
        activityRefreshInterval = setInterval(refreshEmailActivities, 5000);
    }
}

function stopActivityRefresh() {
    if (activityRefreshInterval) {
        clearInterval(activityRefreshInterval);
        activityRefreshInterval = null;
    }
}

async function refreshEmailActivities() {
    try {
        const response = await fetch('/api/email/activities');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const activities = await response.json();
        
        // Ensure activities is an array
        if (Array.isArray(activities)) {
            displayEmailActivities(activities);
        } else {
            console.error('Activities response is not an array:', activities);
            displayEmailActivities([]);
        }
    } catch (error) {
        console.error('Error loading email activities:', error);
        // Don't clear the display on error, just log it
    }
}

function displayEmailActivities(activities) {
    const activityLog = document.getElementById('emailActivity');
    const activityCount = document.getElementById('activityCount');
    
    if (!activityLog) return;
    
    if (!activities || activities.length === 0) {
        activityLog.innerHTML = '<p class="no-activity">No email activity yet</p>';
        if (activityCount) activityCount.textContent = '0 activities';
        return;
    }
    
    if (activityCount) activityCount.textContent = `${activities.length} activities`;
    activityLog.innerHTML = '';
    
    // Display activities in reverse order (newest first)
    const sortedActivities = [...activities].reverse();
    
    sortedActivities.forEach(activity => {
        const activityItem = document.createElement('div');
        activityItem.className = `activity-item activity-${activity.type || 'system'}`;
        
        // Parse timestamp safely
        let timestamp = 'Unknown time';
        try {
            if (activity.timestamp) {
                const date = new Date(activity.timestamp);
                if (!isNaN(date.getTime())) {
                    timestamp = date.toLocaleTimeString();
                }
            }
        } catch (e) {
            console.error('Error parsing timestamp:', e);
        }
        
        const icon = getActivityIcon(activity.type || 'system');
        
        // Build HTML with null checks
        let html = `
            <div class="activity-header">
                <span class="activity-icon">${icon}</span>
                <span class="activity-time">${timestamp}</span>
            </div>
            <div class="activity-message">${activity.message || 'No message'}</div>
        `;
        
        if (activity.subject) {
            html += `<div class="activity-subject">"${activity.subject}"</div>`;
        }
        
        activityItem.innerHTML = html;
        activityLog.appendChild(activityItem);
    });
}

function getActivityIcon(type) {
    const icons = {
        'system': '⚙️',
        'inbox': '📥',
        'sent': '📤',
        'recruitment': '💼',
        'ai': '🤖',
        'error': '❌',
        'skip': '⏭️'
    };
    return icons[type] || '📧';
}

// Dashboard functions
async function loadDashboardData() {
    try {
        const response = await fetch('/api/analytics/summary');
        const data = await response.json();
        
        // Update KPIs
        document.getElementById('kpiTotalJobs').textContent = data.total_jobs;
        document.getElementById('kpiOpenJobs').textContent = data.open_jobs;
        document.getElementById('kpiTotalCVs').textContent = data.total_cvs;
        document.getElementById('kpiInterviews').textContent = data.interviews_scheduled;
        
        // Update charts
        updateCharts(data);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

function updateCharts(data) {
    // Job Status Chart
    const jobStatusData = [{
        values: [data.open_jobs, data.filled_jobs, data.total_jobs - data.open_jobs - data.filled_jobs],
        labels: ['Open', 'Filled', 'Other'],
        type: 'pie',
        marker: {
            colors: ['#007bff', '#28a745', '#6c757d']
        }
    }];
    
    const jobStatusLayout = {
        title: 'Job Status Distribution',
        height: 300
    };
    
    Plotly.newPlot('jobStatusChart', jobStatusData, jobStatusLayout, {responsive: true});
    
    // CV Trend Chart (mock data for now)
    const dates = Array.from({length: 7}, (_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - (6 - i));
        return d.toISOString().split('T')[0];
    });
    
    const cvTrendData = [{
        x: dates,
        y: [12, 15, 18, 14, 20, 16, 22],
        type: 'scatter',
        mode: 'lines+markers',
        name: 'CVs Received',
        line: {
            color: '#007bff',
            width: 2
        }
    }];
    
    const cvTrendLayout = {
        title: 'CV Submissions Trend',
        height: 300,
        xaxis: {
            title: 'Date'
        },
        yaxis: {
            title: 'Count'
        }
    };
    
    Plotly.newPlot('cvTrendChart', cvTrendData, cvTrendLayout, {responsive: true});
}

// Jobs functions
async function loadJobs() {
    try {
        const response = await fetch('/api/jobs');
        const jobs = await response.json();
        
        const tbody = document.getElementById('jobsTableBody');
        tbody.innerHTML = '';
        
        jobs.forEach(job => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${job['JobID'] || ''}</td>
                <td>${job['Job Title'] || ''}</td>
                <td>${job['Project Name'] || ''}</td>
                <td>${job['Job Location (Country)'] || ''}</td>
                <td>${job['Hiring Manager'] || ''}</td>
                <td>${job['Job Status'] || 'Open'}</td>
                <td>
                    <button class="btn btn-sm" onclick="editJob('${job['JobID']}')">Edit</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading jobs:', error);
    }
}

// CVs functions
async function loadCVs() {
    try {
        const response = await fetch('/api/cvs');
        const cvs = await response.json();
        
        const tbody = document.getElementById('cvsTableBody');
        tbody.innerHTML = '';
        
        cvs.forEach(cv => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${cv['CVID'] || ''}</td>
                <td>${cv['Candidate Name'] || ''}</td>
                <td>${cv['Position'] || ''}</td>
                <td>${cv['Project'] || ''}</td>
                <td>${cv['Application Status'] || ''}</td>
                <td>${cv['Interview Date'] || ''}</td>
                <td>
                    <button class="btn btn-sm" onclick="editCV('${cv['CVID']}')">Edit</button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading CVs:', error);
    }
}

// Configuration functions
async function loadConfiguration() {
    await loadHiringManagers();
    await loadProjects();
    await loadCandidates();
}

async function loadHiringManagers() {
    try {
        const response = await fetch('/api/hiring_managers');
        const hms = await response.json();
        
        const hmList = document.getElementById('hmList');
        hmList.innerHTML = '';
        
        hms.forEach(hm => {
            const item = document.createElement('div');
            item.className = 'item-list-item';
            item.innerHTML = `
                <span>${hm.name} (${hm.email})</span>
            `;
            hmList.appendChild(item);
        });
        
        // Update dropdowns
        updateHMDropdowns(hms);
    } catch (error) {
        console.error('Error loading hiring managers:', error);
    }
}

async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        const projects = await response.json();
        
        const projectList = document.getElementById('projectList');
        projectList.innerHTML = '';
        
        projects.forEach(project => {
            const item = document.createElement('div');
            item.className = 'item-list-item';
            item.innerHTML = `
                <span>${project.name}</span>
            `;
            projectList.appendChild(item);
        });
        
        // Update dropdowns
        updateProjectDropdowns(projects);
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

async function loadCandidates() {
    try {
        const response = await fetch('/api/candidates');
        const candidates = await response.json();
        
        const candidateList = document.getElementById('candidateList');
        if (!candidateList) return;
        
        candidateList.innerHTML = '';
        
        candidates.forEach(candidate => {
            const item = document.createElement('div');
            item.className = 'candidate-item';
            
            const details = [];
            if (candidate.email) details.push(candidate.email);
            if (candidate.mobile) details.push(candidate.mobile);
            if (candidate.current_location) details.push(candidate.current_location);
            
            item.innerHTML = `
                <div class="candidate-info">
                    <div class="candidate-name">${candidate.name}</div>
                    <div class="candidate-details">${details.join(' • ')}</div>
                </div>
            `;
            candidateList.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading candidates:', error);
    }
}

function updateHMDropdowns(hms) {
    const selects = document.querySelectorAll('select[name="Hiring Manager"]');
    selects.forEach(select => {
        const currentValue = select.value;
        select.innerHTML = '<option value="">Select Hiring Manager</option>';
        hms.forEach(hm => {
            const option = document.createElement('option');
            option.value = hm.name;
            option.textContent = hm.name;
            select.appendChild(option);
        });
        select.value = currentValue;
    });
}

function updateProjectDropdowns(projects) {
    const selects = document.querySelectorAll('select[name="Project Name"]');
    selects.forEach(select => {
        const currentValue = select.value;
        select.innerHTML = '<option value="">Select Project</option>';
        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.name;
            option.textContent = project.name;
            select.appendChild(option);
        });
        select.value = currentValue;
    });
}

// AI Functions
async function sendAICommand() {
    const input = document.getElementById('aiCommand');
    const command = input.value.trim();
    
    if (!command) return;
    
    // Add user message to chat
    addChatMessage(command, 'user');
    input.value = '';
    
    try {
        const response = await fetch('/api/ai/command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ command })
        });
        
        const result = await response.json();
        
        if (result.error) {
            addChatMessage(`Error: ${result.error}`, 'assistant');
        } else {
            addChatMessage(result.response || 'Command processed successfully', 'assistant');
            
            // Refresh data if needed
            if (command.toLowerCase().includes('add') || command.toLowerCase().includes('update')) {
                refreshData();
            }
        }
    } catch (error) {
        addChatMessage('Failed to process command. Please try again.', 'assistant');
    }
}

function addChatMessage(message, sender) {
    const chatHistory = document.getElementById('aiChatHistory');
    const messageDiv = document.createElement('div');
    messageDiv.className = `ai-message ${sender}`;
    
    if (sender === 'user') {
        messageDiv.innerHTML = `<strong>You:</strong> ${message}`;
    } else {
        messageDiv.innerHTML = `<strong>AI Assistant:</strong> ${message}`;
    }
    
    chatHistory.appendChild(messageDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Modal functions - Make these global
window.showAddJobModal = function() {
    console.log('Showing add job modal');
    document.getElementById('addJobModal').style.display = 'block';
}

window.showAddCVModal = function() {
    console.log('Showing add CV modal');
    loadJobsForDropdown();
    document.getElementById('addCVModal').style.display = 'block';
}

window.showBulkHMModal = function() {
    console.log('Showing bulk HM modal');
    document.getElementById('bulkHMModal').style.display = 'block';
}

window.showBulkProjectModal = function() {
    console.log('Showing bulk project modal');
    document.getElementById('bulkProjectModal').style.display = 'block';
}

window.showBulkCandidateModal = function() {
    console.log('Showing bulk candidate modal');
    document.getElementById('bulkCandidateModal').style.display = 'block';
}

window.showAddCandidateModal = function() {
    console.log('Showing add candidate modal');
    document.getElementById('addCandidateModal').style.display = 'block';
}

window.closeModal = function(modalId) {
    console.log('Closing modal:', modalId);
    document.getElementById(modalId).style.display = 'none';
}

async function loadJobsForDropdown() {
    try {
        const response = await fetch('/api/jobs');
        const jobs = await response.json();
        
        const select = document.querySelector('#addCVForm select[name="JobID"]');
        select.innerHTML = '<option value="">Select Job</option>';
        
        jobs.forEach(job => {
            const option = document.createElement('option');
            option.value = job['JobID'];
            option.textContent = `${job['JobID']} - ${job['Job Title']}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading jobs for dropdown:', error);
    }
}

// Form handlers
async function handleAddJob(e) {
    e.preventDefault();
    console.log('Adding job...');
    
    const formData = new FormData(e.target);
    const jobData = {};
    
    for (let [key, value] of formData.entries()) {
        jobData[key] = value;
    }
    
    jobData['Position Created Date'] = new Date().toISOString().split('T')[0];
    jobData['Job Status'] = 'Open';
    
    try {
        const response = await fetch('/api/jobs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(jobData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(`Job added successfully (ID: ${result.id})`, 'success');
            closeModal('addJobModal');
            e.target.reset();
            loadJobs();
        } else {
            showAlert(result.message || 'Failed to add job', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error adding job', 'error');
    }
}

async function handleAddCV(e) {
    e.preventDefault();
    console.log('Adding CV...');
    
    const formData = new FormData(e.target);
    const cvData = {};
    
    for (let [key, value] of formData.entries()) {
        cvData[key] = value;
    }
    
    cvData['Application Status'] = 'CV Shared';
    cvData['Date CV Shared'] = new Date().toISOString().split('T')[0];
    
    try {
        const response = await fetch('/api/cvs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(cvData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(`CV added successfully (ID: ${result.id})`, 'success');
            closeModal('addCVModal');
            e.target.reset();
            loadCVs();
        } else {
            showAlert(result.message || 'Failed to add CV', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error adding CV', 'error');
    }
}

async function handleAddCandidate(e) {
    e.preventDefault();
    console.log('Adding candidate...');
    
    const formData = new FormData(e.target);
    const candidateData = {};
    
    for (let [key, value] of formData.entries()) {
        candidateData[key] = value;
    }
    
    try {
        const response = await fetch('/api/candidates', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(candidateData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(`Candidate added successfully`, 'success');
            closeModal('addCandidateModal');
            e.target.reset();
            await loadCandidates();
        } else {
            showAlert(result.message || 'Failed to add candidate', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error adding candidate', 'error');
    }
}

// Bulk Import Functions
window.processBulkHM = async function() {
    const textarea = document.getElementById('bulkHMData');
    const data = textarea.value.trim();
    
    if (!data) {
        showAlert('Please enter hiring managers data', 'error');
        return;
    }
    
    // Show progress
    showModalProgress('bulkHMModal', true);
    
    const lines = data.split('\n');
    const hiringManagers = [];
    const errors = [];
    
    lines.forEach((line, index) => {
        const trimmedLine = line.trim();
        if (trimmedLine) {
            const parts = trimmedLine.split(',').map(p => p.trim());
            if (parts.length >= 2 && parts[0] && parts[1]) {
                // Basic email validation
                if (parts[1].includes('@')) {
                    hiringManagers.push({
                        name: parts[0],
                        email: parts[1]
                    });
                } else {
                    errors.push(`Line ${index + 1}: Invalid email format`);
                }
            } else {
                errors.push(`Line ${index + 1}: Invalid format (expected: Name, Email)`);
            }
        }
    });
    
    if (hiringManagers.length === 0) {
        showModalProgress('bulkHMModal', false);
        showModalStatus('bulkHMModal', 'No valid hiring managers found', 'error');
        return;
    }
    
    // Send bulk request
    try {
        const results = [];
        let successCount = 0;
        let errorCount = 0;
        
        for (const hm of hiringManagers) {
            try {
                const response = await fetch('/api/hiring_managers', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(hm)
                });
                
                const result = await response.json();
                if (result.success) {
                    successCount++;
                    results.push(`✓ Added: ${hm.name}`);
                } else {
                    errorCount++;
                    results.push(`✗ Failed: ${hm.name} (possibly duplicate)`);
                }
            } catch (error) {
                errorCount++;
                results.push(`✗ Error: ${hm.name}`);
            }
        }
        
        showModalProgress('bulkHMModal', false);
        
        // Show results
        const summary = `Import complete: ${successCount} added, ${errorCount} failed`;
        showBulkImportResults('bulkHMModal', results, summary);
        
        if (successCount > 0) {
            textarea.value = '';
            await loadHiringManagers();
        }
        
    } catch (error) {
        showModalProgress('bulkHMModal', false);
        showModalStatus('bulkHMModal', 'Import failed: ' + error.message, 'error');
    }
}

window.processBulkProjects = async function() {
    const textarea = document.getElementById('bulkProjectData');
    const data = textarea.value.trim();
    
    if (!data) {
        showAlert('Please enter project names', 'error');
        return;
    }
    
    // Show progress
    showModalProgress('bulkProjectModal', true);
    
    const lines = data.split('\n');
    const projects = lines
        .map(line => line.trim())
        .filter(line => line.length > 0);
    
    if (projects.length === 0) {
        showModalProgress('bulkProjectModal', false);
        showModalStatus('bulkProjectModal', 'No valid projects found', 'error');
        return;
    }
    
    // Send bulk request
    try {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(projects)
        });
        
        const result = await response.json();
        
        showModalProgress('bulkProjectModal', false);
        
        if (result.success) {
            const results = result.results.map(r => 
                r.id ? `✓ Added: ${r.name}` : `✗ Failed: ${r.name} (possibly duplicate)`
            );
            
            const successCount = result.results.filter(r => r.id).length;
            const errorCount = result.results.filter(r => !r.id).length;
            const summary = `Import complete: ${successCount} added, ${errorCount} failed`;
            
            showBulkImportResults('bulkProjectModal', results, summary);
            
            if (successCount > 0) {
                textarea.value = '';
                await loadProjects();
            }
        } else {
            showModalStatus('bulkProjectModal', 'Import failed', 'error');
        }
        
    } catch (error) {
        showModalProgress('bulkProjectModal', false);
        showModalStatus('bulkProjectModal', 'Import failed: ' + error.message, 'error');
    }
}

window.processBulkCandidates = async function() {
    const textarea = document.getElementById('bulkCandidateData');
    const data = textarea.value.trim();
    
    if (!data) {
        showAlert('Please enter candidate data', 'error');
        return;
    }
    
    // Show progress
    showModalProgress('bulkCandidateModal', true);
    
    const lines = data.split('\n');
    const candidates = [];
    const errors = [];
    
    lines.forEach((line, index) => {
        const trimmedLine = line.trim();
        if (trimmedLine) {
            const parts = trimmedLine.split(',').map(p => p.trim());
            if (parts.length >= 1 && parts[0]) {
                candidates.push({
                    name: parts[0],
                    email: parts[1] || '',
                    mobile: parts[2] || '',
                    current_location: parts[3] || '',
                    nationality: parts[4] || '',
                    notice_period: parts[5] || ''
                });
            } else {
                errors.push(`Line ${index + 1}: Name is required`);
            }
        }
    });
    
    if (candidates.length === 0) {
        showModalProgress('bulkCandidateModal', false);
        showModalStatus('bulkCandidateModal', 'No valid candidates found', 'error');
        return;
    }
    
    // Send bulk request
    try {
        const response = await fetch('/api/candidates/bulk', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(candidates)
        });
        
        const result = await response.json();
        
        showModalProgress('bulkCandidateModal', false);
        
        if (result.success) {
            const results = result.results.map(r => 
                r.success ? `✓ Added: ${r.name}` : `✗ Failed: ${r.name} - ${r.error}`
            );
            
            const successCount = result.results.filter(r => r.success).length;
            const errorCount = result.results.filter(r => !r.success).length;
            const summary = `Import complete: ${successCount} added, ${errorCount} failed`;
            
            showBulkImportResults('bulkCandidateModal', results, summary);
            
            if (successCount > 0) {
                textarea.value = '';
                await loadCandidates();
            }
        } else {
            showModalStatus('bulkCandidateModal', 'Import failed', 'error');
        }
        
    } catch (error) {
        showModalProgress('bulkCandidateModal', false);
        showModalStatus('bulkCandidateModal', 'Import failed: ' + error.message, 'error');
    }
}

// Helper functions for bulk import
function showModalProgress(modalId, show) {
    const modal = document.getElementById(modalId);
    let progressDiv = modal.querySelector('.import-progress');
    
    if (!progressDiv) {
        progressDiv = document.createElement('div');
        progressDiv.className = 'import-progress';
        progressDiv.innerHTML = `
            <div class="loading"></div>
            <p>Processing import...</p>
        `;
        modal.querySelector('.modal-content').appendChild(progressDiv);
    }
    
    progressDiv.style.display = show ? 'block' : 'none';
}

function showModalStatus(modalId, message, type) {
    const modal = document.getElementById(modalId);
    let statusDiv = modal.querySelector('.modal-status');
    
    if (!statusDiv) {
        statusDiv = document.createElement('div');
        statusDiv.className = 'modal-status';
        modal.querySelector('.modal-content').appendChild(statusDiv);
    }
    
    statusDiv.className = `modal-status ${type}`;
    statusDiv.textContent = message;
    statusDiv.style.display = 'block';
    
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 5000);
}

function showBulkImportResults(modalId, results, summary) {
    const modal = document.getElementById(modalId);
    let resultsDiv = modal.querySelector('.import-results');
    
    if (!resultsDiv) {
        resultsDiv = document.createElement('div');
        resultsDiv.className = 'import-results';
        modal.querySelector('.modal-content').appendChild(resultsDiv);
    }
    
    const resultsHtml = results.map(r => 
        `<div class="${r.startsWith('✓') ? 'import-success' : 'import-error'}">${r}</div>`
    ).join('');
    
    resultsDiv.innerHTML = `
        ${resultsHtml}
        <div class="import-summary">${summary}</div>
    `;
    
    resultsDiv.style.display = 'block';
}

// Configuration handlers - Make these global
window.saveAIKey = async function() {
    console.log('Saving AI key...');
    const apiKey = document.getElementById('aiApiKey').value.trim();
    
    if (!apiKey) {
        showAlert('Please enter an API key', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/config/ai_key', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ api_key: apiKey })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('AI API key saved successfully', 'success');
            document.getElementById('aiApiKey').value = '';
            await loadSystemStatus();
        } else {
            showAlert('Failed to save API key', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error saving API key', 'error');
    }
}

window.addHiringManager = async function() {
    console.log('Adding hiring manager...');
    const name = document.getElementById('hmName').value.trim();
    const email = document.getElementById('hmEmail').value.trim();
    
    if (!name || !email) {
        showAlert('Please enter both name and email', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/hiring_managers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, email })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('Hiring manager added successfully', 'success');
            document.getElementById('hmName').value = '';
            document.getElementById('hmEmail').value = '';
            loadHiringManagers();
        } else {
            showAlert('Failed to add hiring manager', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error adding hiring manager', 'error');
    }
}

window.addProject = async function() {
    console.log('Adding project...');
    const name = document.getElementById('projectName').value.trim();
    
    if (!name) {
        showAlert('Please enter a project name', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('Project added successfully', 'success');
            document.getElementById('projectName').value = '';
            loadProjects();
        } else {
            showAlert('Failed to add project', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('Error adding project', 'error');
    }
}

// Utility functions
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const content = document.querySelector('.content');
    content.insertBefore(alertDiv, content.firstChild);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

window.exportData = function(type) {
    console.log('Exporting data:', type);
    window.location.href = `/api/export/${type}`;
}

window.refreshEmailActivities = refreshEmailActivities;

async function refreshData() {
    await loadSystemStatus();
    
    switch(currentTab) {
        case 'dashboard':
            await loadDashboardData();
            break;
        case 'jobs':
            await loadJobs();
            break;
        case 'cvs':
            await loadCVs();
            break;
    }
}

// Placeholder functions for edit buttons
window.editJob = function(jobId) {
    console.log('Edit job:', jobId);
    showAlert('Edit functionality coming soon', 'info');
}

window.editCV = function(cvId) {
    console.log('Edit CV:', cvId);
    showAlert('Edit functionality coming soon', 'info');
}

// Close modals when clicking outside
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}

console.log('App.js loaded successfully');

// Add this debug version to your app.js temporarily to see what's happening

function displayEmailActivities(activities) {
    console.log('displayEmailActivities called with:', activities);
    
    const activityLog = document.getElementById('emailActivity');
    const activityCount = document.getElementById('activityCount');
    
    if (!activityLog) {
        console.error('Activity log element not found!');
        return;
    }
    
    if (!activities || activities.length === 0) {
        activityLog.innerHTML = '<p class="no-activity">No email activity yet</p>';
        if (activityCount) activityCount.textContent = '0 activities';
        return;
    }
    
    if (activityCount) activityCount.textContent = `${activities.length} activities`;
    activityLog.innerHTML = '';
    
    // Display activities in reverse order (newest first)
    const sortedActivities = [...activities].reverse();
    
    sortedActivities.forEach((activity, index) => {
        console.log(`Activity ${index}:`, activity);
        
        const activityItem = document.createElement('div');
        activityItem.className = `activity-item activity-${activity.type || 'system'}`;
        
        // Parse timestamp safely
        let timestamp = 'Unknown time';
        try {
            if (activity.timestamp) {
                const date = new Date(activity.timestamp);
                if (!isNaN(date.getTime())) {
                    timestamp = date.toLocaleTimeString();
                } else {
                    console.warn('Invalid timestamp:', activity.timestamp);
                }
            } else {
                console.warn('No timestamp for activity:', activity);
            }
        } catch (e) {
            console.error('Error parsing timestamp:', e);
        }
        
        const icon = getActivityIcon(activity.type || 'system');
        
        // Build HTML with null checks
        let html = `
            <div class="activity-header">
                <span class="activity-icon">${icon}</span>
                <span class="activity-time">${timestamp}</span>
            </div>
            <div class="activity-message">${activity.message || 'No message'}</div>
        `;
        
        if (activity.subject) {
            html += `<div class="activity-subject">"${activity.subject}"</div>`;
        }
        
        activityItem.innerHTML = html;
        activityLog.appendChild(activityItem);
    });
}

// Also add this enhanced version of refreshEmailActivities
async function refreshEmailActivities() {
    console.log('Refreshing email activities...');
    
    try {
        const response = await fetch('/api/email/activities');
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const activities = await response.json();
        console.log('Activities received:', activities);
        
        // Ensure activities is an array
        if (Array.isArray(activities)) {
            displayEmailActivities(activities);
        } else {
            console.error('Activities response is not an array:', activities);
            displayEmailActivities([]);
        }
    } catch (error) {
        console.error('Error loading email activities:', error);
    }
}

// Make sure the refresh button works
window.refreshEmailActivities = refreshEmailActivities;
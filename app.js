document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const tabButtons = document.querySelectorAll('.tab-btn');
    const resultTabButtons = document.querySelectorAll('[data-result-tab]');
    const startRecordingBtn = document.getElementById('start-recording');
    const stopRecordingBtn = document.getElementById('stop-recording');
    const uploadForm = document.getElementById('upload-form');
    const textForm = document.getElementById('text-form');
    const exportBtn = document.getElementById('export-btn');
    const exportDropdown = document.getElementById('export-dropdown');
    const exportTasksBtn = document.getElementById('export-tasks-btn');
    const taskManagerDropdown = document.getElementById('task-manager-dropdown');
    const credentialsModal = document.getElementById('credentials-modal');
    const credentialsForm = document.getElementById('credentials-form');
    const closeModalBtn = document.querySelector('.close-modal');
    const cancelCredentialsBtn = document.getElementById('cancel-credentials');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    const resultsSection = document.getElementById('results-section');
    const liveTranscriptContainer = document.getElementById('live-transcript-container');
    const liveTranscript = document.getElementById('live-transcript');
    const timeDisplay = document.getElementById('time-display');
    const statusText = document.getElementById('status-text');
    const recordingIndicator = document.querySelector('.recording-indicator');
    const audioFileInput = document.getElementById('audio-file');
    const fileNameDisplay = document.getElementById('file-name');
    const uploadProgress = document.querySelector('.upload-progress');
    const progressFill = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-text');
    const exportCustomBtn = document.getElementById('export-custom-btn');
    const customExportForm = document.getElementById('custom-export-form');
    const customExportModal = document.getElementById('custom-export-modal');
    const closeCustomExportModalBtn = document.querySelector('.close-custom-export-modal');
    const cancelCustomExportBtn = document.getElementById('cancel-custom-export');

    // State variables
    let isRecording = false;
    let recordingTimer = null;
    let recordingSeconds = 0;
    let currentExportSystem = null;
    let eventSource = null;

    // Tab navigation
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            
            // Update active tab button
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Show active tab content
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('active');
            });
            document.getElementById(`${tabId}-tab`).classList.add('active');
        });
    });

    // Results tab navigation
    resultTabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-result-tab');
            
            // Update active tab button
            resultTabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Show active tab content
            document.querySelectorAll('.result-tab-pane').forEach(pane => {
                pane.classList.remove('active');
            });
            document.getElementById(`${tabId}-tab`).classList.add('active');
        });
    });

    // Recording functionality
    startRecordingBtn.addEventListener('click', startRecording);
    stopRecordingBtn.addEventListener('click', stopRecording);

    function startRecording() {
        isRecording = true;
        startRecordingBtn.disabled = true;
        stopRecordingBtn.disabled = false;
        recordingIndicator.classList.remove('hidden');
        statusText.textContent = 'Recording in progress...';
        liveTranscriptContainer.classList.remove('hidden');
        liveTranscript.innerHTML = '';
        
        // Reset timer
        recordingSeconds = 0;
        updateTimeDisplay();
        
        // Start timer
        recordingTimer = setInterval(() => {
            recordingSeconds++;
            updateTimeDisplay();
        }, 1000);
        
        // Start live transcription
        startLiveTranscription();
    }

    function stopRecording() {
        isRecording = false;
        startRecordingBtn.disabled = false;
        stopRecordingBtn.disabled = true;
        recordingIndicator.classList.add('hidden');
        statusText.textContent = 'Processing recording...';
        
        // Stop timer
        clearInterval(recordingTimer);
        
        // Stop live transcription and process results
        if (eventSource) {
            eventSource.close();
        }
        
        showLoading('Generating meeting summary...');
        
        // Send request to stop transcription and get results
        fetch('/api/stop-transcription', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayResults(data);
            } else {
                showError('Error processing recording: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            showError('Error: ' + error.message);
        })
        .finally(() => {
            hideLoading();
            statusText.textContent = 'Ready to record';
        });
    }

    function updateTimeDisplay() {
        const minutes = Math.floor(recordingSeconds / 60);
        const seconds = recordingSeconds % 60;
        timeDisplay.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    function startLiveTranscription() {
        // Close any existing connection
        if (eventSource) {
            eventSource.close();
        }
        
        // Connect to SSE endpoint
        eventSource = new EventSource('/api/live-transcription');
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.segment) {
                const p = document.createElement('p');
                p.textContent = data.segment;
                liveTranscript.appendChild(p);
                liveTranscript.scrollTop = liveTranscript.scrollHeight;
            }
        };
        
        eventSource.onerror = function() {
            console.error('SSE connection error');
            eventSource.close();
        };
    }

    // File upload functionality
    audioFileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            fileNameDisplay.textContent = this.files[0].name;
        } else {
            fileNameDisplay.textContent = '';
        }
    });

    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const fileInput = document.getElementById('audio-file');
        
        if (!fileInput.files.length) {
            showError('Please select a file to upload');
            return;
        }
        
        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);
        
        // Show progress
        uploadProgress.classList.remove('hidden');
        progressFill.style.width = '0%';
        progressText.textContent = 'Uploading: 0%';
        
        showLoading('Uploading and processing audio file...');
        
        // Use XMLHttpRequest to track upload progress
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/upload', true);
        
        xhr.upload.onprogress = function(e) {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                progressFill.style.width = percentComplete + '%';
                progressText.textContent = `Uploading: ${percentComplete}%`;
            }
        };
        
        xhr.onload = function() {
            uploadProgress.classList.add('hidden');
            
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                displayResults(response);
            } else {
                try {
                    const response = JSON.parse(xhr.responseText);
                    showError('Error: ' + (response.error || 'Unknown error'));
                } catch {
                    showError('Error uploading file');
                }
            }
            hideLoading();
        };
        
        xhr.onerror = function() {
            uploadProgress.classList.add('hidden');
            showError('Error uploading file');
            hideLoading();
        };
        
        xhr.send(formData);
    });

    // Text analysis functionality
    textForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const transcriptText = document.getElementById('transcript-text').value.trim();
        
        if (!transcriptText) {
            showError('Please enter a transcript to analyze');
            return;
        }
        
        showLoading('Analyzing transcript...');
        
        fetch('/api/process-text', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                transcript: transcriptText
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Add transcript to the results since it's not returned by the API
                data.transcript = transcriptText;
                displayResults(data);
            } else {
                showError('Error analyzing text: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            showError('Error: ' + error.message);
        })
        .finally(() => {
            hideLoading();
        });
    });

    // Export dropdown functionality
    exportBtn.addEventListener('click', function() {
        exportDropdown.classList.toggle('hidden');
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        if (!exportBtn.contains(e.target) && !exportDropdown.contains(e.target)) {
            exportDropdown.classList.add('hidden');
        }
        
        if (!exportTasksBtn.contains(e.target) && !taskManagerDropdown.contains(e.target)) {
            taskManagerDropdown.classList.add('hidden');
        }
    });

    // Export format selection
    document.querySelectorAll('#export-dropdown .dropdown-item').forEach(button => {
        button.addEventListener('click', function() {
            const format = this.getAttribute('data-format');
            exportFormat(format);
            exportDropdown.classList.add('hidden');
        });
    });

    function exportFormat(format) {
        showLoading(`Exporting as ${format}...`);
        
        fetch('/api/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                format: format
            })
        })
        .then(response => {
            if (response.ok) {
                return response.blob();
            } else {
                return response.json().then(data => {
                    throw new Error(data.error || 'Export failed');
                });
            }
        })
        .then(blob => {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `meeting_summary.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch(error => {
            showError('Error exporting: ' + error.message);
        })
        .finally(() => {
            hideLoading();
        });
    }

    // Task manager export functionality
    exportTasksBtn.addEventListener('click', function() {
        var dropdown = document.getElementById('task-manager-dropdown');
        console.log("Export to Task Manager button clicked!"); // Debugging
        dropdown.classList.toggle('hidden');
        console.log("Dropdown class list:", dropdown.classList); // Check if 'hidden' is removed
    });
    

    document.querySelectorAll('#task-manager-dropdown .dropdown-item').forEach(button => {
        button.addEventListener('click', function() {
            const system = this.getAttribute('data-system');
            currentExportSystem = system;
            showCredentialsModal(system);
            taskManagerDropdown.classList.add('hidden');
        });
    });

    function showCredentialsModal(system) {
        // Clear previous fields
        const credentialFields = document.getElementById('credential-fields');
        credentialFields.innerHTML = '';
        
        // Add appropriate fields based on selected system
        if (system === 'jira') {
            addCredentialField('api_key', 'API Key', 'password');
            addCredentialField('url', 'Jira URL', 'url');
        } else if (system === 'trello') {
            addCredentialField('api_key', 'API Key', 'password');
            addCredentialField('token', 'Token', 'password');
        } else if (system === 'asana') {
            addCredentialField('api_key', 'API Key', 'password');
        } else if (system === 'github') {
            addCredentialField('token', 'Personal Access Token', 'password');
        } else if (system === 'notion') {
            addCredentialField('token', 'Integration Token', 'password');
        }
        
        // Show modal
        credentialsModal.classList.remove('hidden');
    }

    function addCredentialField(name, label, type) {
        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'form-group';
        
        const labelElement = document.createElement('label');
        labelElement.textContent = label;
        labelElement.setAttribute('for', name);
        
        const input = document.createElement('input');
        input.type = type;
        input.id = name;
        input.name = name;
        input.required = true;
        
        fieldDiv.appendChild(labelElement);
        fieldDiv.appendChild(input);
        
        document.getElementById('credential-fields').appendChild(fieldDiv);
    }

    // Handle credential submission
    credentialsForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Collect credentials
        const credentials = {};
        const inputs = credentialsForm.querySelectorAll('input');
        inputs.forEach(input => {
            credentials[input.name] = input.value;
        });
        
        // Close modal
        credentialsModal.classList.add('hidden');
        
        // Export tasks
        exportTasks(currentExportSystem, credentials);
    });

    // Close modal buttons
    closeModalBtn.addEventListener('click', function() {
        credentialsModal.classList.add('hidden');
    });

    cancelCredentialsBtn.addEventListener('click', function() {
        credentialsModal.classList.add('hidden');
    });

    function exportTasks(system, credentials) {
        showLoading(`Exporting tasks to ${system}...`);
        
        fetch('/api/export-tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                system: system,
                credentials: credentials
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showError('Export failed: ' + data.error);
            } else {
                showSuccess(`Tasks exported to ${system} successfully!`);
            }
        })
        .catch(error => {
            showError('Error: ' + error.message);
        })
        .finally(() => {
            hideLoading();
        });
    }

    // Display the analysis results
    function displayResults(data) {
        // Show results section
        resultsSection.classList.remove('hidden');
        
        // Populate the summary tab
        document.getElementById('summary-content').textContent = data.summary;
        
        // Populate key points
        const keyPointsContent = document.getElementById('key-points-content');
        keyPointsContent.innerHTML = '';
        if (data.key_points && data.key_points.length > 0) {
            const ul = document.createElement('ul');
            data.key_points.forEach(point => {
                const li = document.createElement('li');
                li.textContent = point;
                ul.appendChild(li);
            });
            keyPointsContent.appendChild(ul);
        } else {
            keyPointsContent.textContent = 'No key points identified.';
        }
        
        // Populate decisions
        const decisionsContent = document.getElementById('decisions-content');
        decisionsContent.innerHTML = '';
        if (data.decisions && data.decisions.length > 0) {
            const ul = document.createElement('ul');
            data.decisions.forEach(decision => {
                const li = document.createElement('li');
                li.textContent = decision;
                ul.appendChild(li);
            });
            decisionsContent.appendChild(ul);
        } else {
            decisionsContent.textContent = 'No decisions identified.';
        }
        
        // Populate action items
        const actionItemsContent = document.getElementById('action-items-content');
        actionItemsContent.innerHTML = '';
        if (data.action_items && data.action_items.length > 0) {
            const table = document.createElement('table');
            table.className = 'action-items-table';
            
            // Create header
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            ['Task', 'Assignee', 'Status', 'Created'].forEach(text => {
                const th = document.createElement('th');
                th.textContent = text;
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);
            
            // Create body
            const tbody = document.createElement('tbody');
            data.action_items.forEach(item => {
                const row = document.createElement('tr');
                
                const taskCell = document.createElement('td');
                taskCell.textContent = item.task;
                
                const assigneeCell = document.createElement('td');
                assigneeCell.textContent = item.assignee || 'Not assigned';
                
                const statusCell = document.createElement('td');
                const statusBadge = document.createElement('span');
                statusBadge.className = 'status-badge ' + item.status;
                statusBadge.textContent = item.status.charAt(0).toUpperCase() + item.status.slice(1);
                statusCell.appendChild(statusBadge);
                
                const createdCell = document.createElement('td');
                createdCell.textContent = item.created || 'N/A';
                
                row.appendChild(taskCell);
                row.appendChild(assigneeCell);
                row.appendChild(statusCell);
                row.appendChild(createdCell);
                
                tbody.appendChild(row);
            });
            table.appendChild(tbody);
            
            actionItemsContent.appendChild(table);
        } else {
            actionItemsContent.textContent = 'No action items identified.';
        }
        
        // Populate transcript
        const transcriptContent = document.getElementById('transcript-content');
        transcriptContent.innerHTML = '';
        if (data.transcript) {
            // Format with timestamps if they exist
            const lines = data.transcript.split('\n');
            lines.forEach(line => {
                if (line.trim()) {
                    const p = document.createElement('p');
                    
                    // Check for timestamp pattern [MM:SS]
                    if (line.match(/^\[\d{2}:\d{2}\]/)) {
                        const timestamp = line.substring(0, 7);
                        const text = line.substring(7).trim();
                        
                        const timestampSpan = document.createElement('span');
                        timestampSpan.className = 'transcript-timestamp';
                        timestampSpan.textContent = timestamp;
                        
                        p.appendChild(timestampSpan);
                        p.appendChild(document.createTextNode(' ' + text));
                    } else {
                        p.textContent = line;
                    }
                    
                    transcriptContent.appendChild(p);
                }
            });
        } else {
            transcriptContent.textContent = 'No transcript available.';
        }
        
        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    // UI Helper Functions
    function showLoading(message) {
        loadingText.textContent = message || 'Loading...';
        loadingOverlay.classList.remove('hidden');
    }

    function hideLoading() {
        loadingOverlay.classList.add('hidden');
    }

    function showError(message) {
        // Create toast notification for error
        const toast = document.createElement('div');
        toast.className = 'toast error';
        toast.textContent = message;
        document.body.appendChild(toast);
        
        // Remove after 5 seconds
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 500);
        }, 5000);
    }

    function showSuccess(message) {
        // Create toast notification for success
        const toast = document.createElement('div');
        toast.className = 'toast success';
        toast.textContent = message;
        document.body.appendChild(toast);
        
        // Remove after 5 seconds
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 500);
        }, 5000);
    }

    // About link 
    document.getElementById('about-link').addEventListener('click', function(e) {
        e.preventDefault();
        
        const aboutContent = `
            <div class="about-modal">
                <h2>About AI Meeting Summarizer</h2>
                <p>AI Meeting Summarizer is a tool that helps teams save time by automatically extracting key information from meetings.</p>
                <h3>Features:</h3>
                <ul>
                    <li>Record meetings or upload audio files</li>
                    <li>Live transcription as you speak</li>
                    <li>Extract key points, decisions, and action items</li>
                    <li>Export to various formats</li>
                    <li>Integration with task management systems</li>
                </ul>
                <p>Version 1.0.0</p>
            </div>
        `;
        
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <button class="close-modal">&times;</button>
                </div>
                <div class="modal-body">
                    ${aboutContent}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Remove hidden class after a small delay to trigger transition
        setTimeout(() => {
            modal.classList.remove('hidden');
        }, 10);
        
        // Close button functionality
        modal.querySelector('.close-modal').addEventListener('click', function() {
            modal.classList.add('hidden');
            setTimeout(() => {
                document.body.removeChild(modal);
            }, 300);
        });
    });

    // Export custom format functionality
    exportCustomBtn.addEventListener('click', function() {
        customExportModal.classList.remove('hidden');
    });

    customExportForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formatOptions = {
            sections: Array.from(customExportForm.querySelectorAll('input[name="sections"]:checked')).map(input => input.value),
            style: customExportForm.querySelector('input[name="style"]:checked').value,
            date_format: customExportForm.querySelector('input[name="date_format"]').value,
            include_timestamps: customExportForm.querySelector('input[name="include_timestamps"]').checked,
            action_item_format: customExportForm.querySelector('input[name="action_item_format"]:checked').value,
            highlight_terms: customExportForm.querySelector('input[name="highlight_terms"]').value.split(',').map(term => term.trim()),
            sort_action_items_by: customExportForm.querySelector('select[name="sort_action_items_by"]').value,
            max_transcript_length: parseInt(customExportForm.querySelector('input[name="max_transcript_length"]').value, 10)
        };

        showLoading('Exporting custom summary...');

        fetch('/api/export-custom', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                format_options: formatOptions
            })
        })
        .then(response => {
            if (response.ok) {
                return response.blob();
            } else {
                return response.json().then(data => {
                    throw new Error(data.error || 'Export failed');
                });
            }
        })
        .then(blob => {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'custom_meeting_summary.txt';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch(error => {
            showError('Error exporting: ' + error.message);
        })
        .finally(() => {
            hideLoading();
            customExportModal.classList.add('hidden');
        });
    });

    // Close custom export modal buttons
    closeCustomExportModalBtn.addEventListener('click', function() {
        customExportModal.classList.add('hidden');
    });

    cancelCustomExportBtn.addEventListener('click', function() {
        customExportModal.classList.add('hidden');
    });

    document.getElementById('export-tasks-btn').addEventListener('click', function() {
        const dropdown = document.getElementById('task-manager-dropdown');
        dropdown.classList.toggle('hidden');
    });

    // Add event listeners for dropdown items
    document.querySelectorAll('#task-manager-dropdown .dropdown-item').forEach(item => {
        item.addEventListener('click', function() {
            const system = this.getAttribute('data-system');
            exportTasksToSystem(system);
        });
    });

    function exportTasksToSystem(system) {
        const tasks = getTasksFromUI(); // Implement this function to gather tasks from the UI
        fetch('/api/export-tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ platform: system, tasks: tasks })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Tasks exported successfully!');
            } else {
                alert('Error exporting tasks: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while exporting tasks.');
        });
    }
});
function exportTasks(platform) {
    const tasks = [];

    document.querySelectorAll("#action-items-table tbody tr").forEach(row => {
        const cells = row.querySelectorAll("td");
        if (cells.length === 4) {
            tasks.push({
                task: cells[0].innerText,
                assignee: cells[1].innerText,
                status: cells[2].innerText,
                created: cells[3].innerText
            });
        }
    });

    fetch("/api/export-tasks", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ platform, tasks })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            alert("Tasks successfully exported to " + platform);
        } else {
            alert("Failed to export tasks: " + data.message);
        }
    })
    .catch(error => console.error("Error exporting tasks:", error));
}

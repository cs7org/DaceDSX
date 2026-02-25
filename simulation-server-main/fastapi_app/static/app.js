const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileListEl = document.getElementById('file-list');
const submitBtn = document.getElementById('submit-btn');

let selectedFiles = [];

// --- Drag & Drop ---
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    addFiles(e.dataTransfer.files);
});

// --- File Input ---
fileInput.addEventListener('change', () => {
    addFiles(fileInput.files);
    fileInput.value = '';
});

function addFiles(fileListObj) {
    for (const f of fileListObj) {
        if (!selectedFiles.find(s => s.name === f.name && s.size === f.size)) {
            selectedFiles.push(f);
        }
    }
    renderFileList();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function renderFileList() {
    fileListEl.innerHTML = selectedFiles.map((f, i) =>
        `<li>
            <span class="name">${f.name}</span>
            <span class="size">${formatSize(f.size)}</span>
            <button class="remove" onclick="removeFile(${i})">✕</button>
        </li>`
    ).join('');
    submitBtn.disabled = selectedFiles.length === 0;
}

// --- Submit ---
async function submitSimulation() {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Uploading...';

    const formData = new FormData();
    selectedFiles.forEach(f => formData.append('files', f));

    try {
        const res = await fetch('/submit', { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok) {
            alert('Error: ' + (data.error || 'Submission failed'));
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Simulation';
            return;
        }

        const taskId = data.task_id;

        // Show status card
        document.getElementById('upload-card').classList.add('hidden');
        document.getElementById('status-card').classList.remove('hidden');
        document.getElementById('task-id-display').textContent = 'Task ID: ' + taskId;
        setStatus('pending', 'Queued — waiting for a worker...');

        // Poll for results
        const poll = setInterval(async () => {
            const check = await fetch('/check/' + taskId);
            const status = await check.json();

            if (status.status === 'RUNNING') {
                setStatus('running', 'Simulation is running...');
            } else if (status.status === 'DONE') {
                clearInterval(poll);
                setStatus('done', 'Simulation complete!');
                showResults(taskId, status.downloads || []);
            } else if (status.status === 'ERROR') {
                clearInterval(poll);
                setStatus('error', 'Error: ' + (status.error || 'Unknown error'));
            }
        }, 2000);

    } catch (err) {
        alert('Network error: ' + err.message);
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Simulation';
    }
}

function setStatus(type, message) {
    const bar = document.getElementById('status-bar');
    bar.className = 'status-bar ' + type;
    document.getElementById('status-text').textContent = message;
    document.getElementById('status-spinner').style.display =
        (type === 'done' || type === 'error') ? 'none' : 'block';
}

function showResults(taskId, downloads) {
    const resultsCard = document.getElementById('results-card');
    const resultsList = document.getElementById('results-list');
    resultsCard.classList.remove('hidden');

    if (downloads.length === 0) {
        resultsList.innerHTML = '<li>No result files found.</li>';
        return;
    }

    resultsList.innerHTML = downloads.map(url => {
        const filename = url.split('/').pop();
        return `<li><a href="${url}" download>${filename}</a></li>`;
    }).join('');
}

function resetForm() {
    selectedFiles = [];
    renderFileList();
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submit Simulation';
    document.getElementById('upload-card').classList.remove('hidden');
    document.getElementById('status-card').classList.add('hidden');
    document.getElementById('results-card').classList.add('hidden');
}

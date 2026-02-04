const textPanel = document.getElementById('text-panel');
const jsonPanel = document.getElementById('json-panel');
const askPanel = document.getElementById('ask-panel');
const uploadPanel = document.getElementById('upload-panel');
const askPatientPanel = document.getElementById('ask-patient-panel');
const textInput = document.getElementById('availability-text');
const jsonInput = document.getElementById('availability-json');
const askInput = document.getElementById('ask-question');
const askPatientInput = document.getElementById('ask-patient-question');
const fileInput = document.getElementById('file-upload');
const uploadBtn = document.getElementById('upload-btn');
const uploadStatus = document.getElementById('upload-status');
const submitBtn = document.getElementById('submit-btn');
const btnText = submitBtn.querySelector('.btn-text');
const resultsEl = document.getElementById('results');
const askResultsEl = document.getElementById('ask-results');
const slotsList = document.getElementById('slots-list');
const noSlotsEl = document.getElementById('no-slots');
const answerContentEl = document.getElementById('answer-content');
const answerSourcesEl = document.getElementById('answer-sources');
const errorEl = document.getElementById('error');

let mode = 'text';

const EXAMPLE_PROMPT = `Dr. Smith is available Monday through Friday, 9am to 5pm Eastern time. Patient prefers morning slots before noon. Looking for appointments between Feb 3 and Feb 10, 2025. There's already a meeting on Feb 3 from 10:00 to 10:30am. Use 30-minute slots with 10 minutes buffer between appointments.`;

const EXAMPLE_QUESTION = 'What timezone formats are supported?';

const EXAMPLE_PATIENT_QUESTION = 'What are the patient\'s current medications?';

document.getElementById('try-example').addEventListener('click', () => {
  document.querySelector('.tab[data-mode="text"]').click();
  textInput.value = EXAMPLE_PROMPT;
  textInput.focus();
});

document.getElementById('try-ask-patient-example').addEventListener('click', () => {
  document.querySelector('.tab[data-mode="ask_patient"]').click();
  askPatientInput.value = EXAMPLE_PATIENT_QUESTION;
  askPatientInput.focus();
});

uploadBtn.addEventListener('click', async () => {
  const files = fileInput.files;
  if (!files || files.length === 0) {
    uploadStatus.textContent = 'Please select files to upload.';
    uploadStatus.className = 'upload-status error';
    return;
  }

  uploadStatus.textContent = 'Uploading...';
  uploadStatus.className = 'upload-status';

  for (let file of files) {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/upload', {
        method: 'POST',
        body: formData,
      });

      const result = await res.json();
      if (!res.ok) {
        throw new Error(result.detail || `Upload failed (${res.status})`);
      }

      uploadStatus.textContent = `✓ ${result.message}`;
      uploadStatus.className = 'upload-status success';
    } catch (err) {
      uploadStatus.textContent = `✗ Failed to upload ${file.name}: ${err.message}`;
      uploadStatus.className = 'upload-status error';
      break;
    }
  }
});

document.querySelectorAll('.tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    mode = tab.dataset.mode;
    document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
    tab.classList.add('active');
    if (mode === 'text') textPanel.classList.add('active');
    else if (mode === 'json') jsonPanel.classList.add('active');
    else if (mode === 'ask') askPanel.classList.add('active');
    else if (mode === 'upload') uploadPanel.classList.add('active');
    else if (mode === 'ask_patient') askPatientPanel.classList.add('active');
    btnText.textContent = (mode === 'ask' || mode === 'ask_patient') ? 'Ask' : mode === 'upload' ? 'Upload' : 'Get suggestions';
    resultsEl.classList.add('hidden');
    askResultsEl.classList.add('hidden');
    hideError();
  });
});

submitBtn.addEventListener('click', async () => {
  hideError();
  if (mode === 'ask') {
    const q = askInput.value.trim();
    if (!q) {
      showError('Please enter a question.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      });
      const text = await res.text();
      let data;
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        showError(res.ok ? 'Invalid response from server.' : (text || `Server error (${res.status})`));
        return;
      }
      if (!res.ok) {
        const msg = Array.isArray(data.detail)
          ? data.detail.map((d) => d.msg || d.loc?.join('.')).join(' ')
          : (typeof data.detail === 'string' ? data.detail : null) || `Request failed (${res.status})`;
        showError(msg);
        return;
      }
      answerContentEl.textContent = data.answer;
      answerSourcesEl.textContent = data.sources?.length ? `Sources: ${data.sources.join(', ')}` : '';
      askResultsEl.classList.remove('hidden');
      askResultsEl.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
      showError(err.message || 'Network error. Is the server running?');
    } finally {
      setLoading(false);
    }
    return;
  }

  if (mode === 'ask_patient') {
    const q = askPatientInput.value.trim();
    if (!q) {
      showError('Please enter a question.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('/ask_patient', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      });
      const text = await res.text();
      let data;
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        showError(res.ok ? 'Invalid response from server.' : (text || `Server error (${res.status})`));
        return;
      }
      if (!res.ok) {
        const msg = Array.isArray(data.detail)
          ? data.detail.map((d) => d.msg || d.loc?.join('.')).join(' ')
          : (typeof data.detail === 'string' ? data.detail : null) || `Request failed (${res.status})`;
        showError(msg);
        return;
      }
      answerContentEl.textContent = data.answer;
      answerSourcesEl.textContent = data.sources?.length ? `Sources: ${data.sources.join(', ')}` : '';
      askResultsEl.classList.remove('hidden');
      askResultsEl.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
      showError(err.message || 'Network error. Is the server running?');
    } finally {
      setLoading(false);
    }
    return;
  }

  const body = mode === 'text'
    ? { availability_text: textInput.value.trim() }
    : (() => {
        try {
          return JSON.parse(jsonInput.value.trim());
        } catch {
          showError('Invalid JSON. Please check the format.');
          return null;
        }
      })();

  if (!body) return;
  if (mode === 'text' && !body.availability_text) {
    showError('Please enter availability text.');
    return;
  }
  if (mode === 'json' && !body.structured_availability) {
    showError('JSON must include a "structured_availability" object.');
    return;
  }

  setLoading(true);
  try {
    const res = await fetch('/suggest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const text = await res.text();
    let data;
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      showError(res.ok ? 'Invalid response from server.' : (text || `Server error (${res.status})`));
      return;
    }

    if (!res.ok) {
      const msg = Array.isArray(data.detail)
        ? data.detail.map((d) => d.msg || d.loc?.join('.')).join(' ')
        : (typeof data.detail === 'string' ? data.detail : null) || `Request failed (${res.status})`;
      showError(msg);
      return;
    }

    renderSlots(data.slots);
    resultsEl.classList.remove('hidden');
    resultsEl.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    showError(err.message || 'Network error. Is the server running?');
  } finally {
    setLoading(false);
  }
});

function renderSlots(slots) {
  slotsList.innerHTML = '';
  noSlotsEl.classList.add('hidden');

  if (!slots || slots.length === 0) {
    noSlotsEl.classList.remove('hidden');
    return;
  }

  slots.forEach((slot) => {
    const card = document.createElement('div');
    card.className = 'slot-card';
    const start = new Date(slot.start_iso);
    const end = new Date(slot.end_iso);
    const timeStr = `${formatDateTime(start)} – ${formatTime(end)}`;
    card.innerHTML = `
      <div class="slot-time">${timeStr}</div>
      <div class="slot-provider">Provider: ${escapeHtml(slot.provider_id)}</div>
      <div class="slot-explanation">${escapeHtml(slot.explanation)}</div>
    `;
    slotsList.appendChild(card);
  });
}

function formatDateTime(d) {
  return d.toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function formatTime(d) {
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

function setLoading(loading) {
  submitBtn.disabled = loading;
  submitBtn.classList.toggle('loading', loading);
}

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.classList.remove('hidden');
}

function hideError() {
  errorEl.classList.add('hidden');
}

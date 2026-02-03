const textPanel = document.getElementById('text-panel');
const jsonPanel = document.getElementById('json-panel');
const textInput = document.getElementById('availability-text');
const jsonInput = document.getElementById('availability-json');
const submitBtn = document.getElementById('submit-btn');
const resultsEl = document.getElementById('results');
const slotsList = document.getElementById('slots-list');
const noSlotsEl = document.getElementById('no-slots');
const errorEl = document.getElementById('error');

let mode = 'text';

const EXAMPLE_PROMPT = `Dr. Smith is available Monday through Friday, 9am to 5pm Eastern time. Patient prefers morning slots before noon. Looking for appointments between Feb 3 and Feb 10, 2025. There's already a meeting on Feb 3 from 10:00 to 10:30am. Use 30-minute slots with 10 minutes buffer between appointments.`;

document.getElementById('try-example').addEventListener('click', () => {
  document.querySelector('.tab[data-mode="text"]').click();
  textInput.value = EXAMPLE_PROMPT;
  textInput.focus();
});

document.querySelectorAll('.tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    mode = tab.dataset.mode;
    document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
    tab.classList.add('active');
    (mode === 'text' ? textPanel : jsonPanel).classList.add('active');
    hideError();
  });
});

submitBtn.addEventListener('click', async () => {
  hideError();
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

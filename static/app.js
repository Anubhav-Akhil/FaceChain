/**
 * app.js — Frontend logic for the Face ID + Blockchain Pipeline Web UI.
 *
 * Handles:
 *  - Drag-and-drop image upload with preview
 *  - SSE streaming of pipeline progress
 *  - Dynamic DOM updates for each pipeline stage
 *  - Matched results gallery with filtering
 *  - Copy-to-clipboard utility
 */

// ── DOM Elements ──────────────────────────────────────────────
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const uploadPreview = document.getElementById('upload-preview');
const previewImg = document.getElementById('preview-img');
const previewName = document.getElementById('preview-name');
const previewSize = document.getElementById('preview-size');
const modelSelect = document.getElementById('model-select');
const runBtn = document.getElementById('run-btn');

const pipelineSection = document.getElementById('pipeline-section');
const resultsSection = document.getElementById('results-section');
const matchesSection = document.getElementById('matches-section');
const summaryBar = document.getElementById('summary-bar');
const errorBanner = document.getElementById('error-banner');
const errorText = document.getElementById('error-text');

// ── Webcam Elements ───────────────────────────────────────────
const tabFileMode = document.getElementById('tab-file-mode');
const tabWebcamMode = document.getElementById('tab-webcam-mode');
const webcamZone = document.getElementById('webcam-zone');
const webcamVideo = document.getElementById('webcam-video');
const webcamCanvas = document.getElementById('webcam-canvas');
const webcamFlash = document.getElementById('webcam-flash');
const btnCapturePhoto = document.getElementById('btn-capture-photo');
const btnRetakePhoto = document.getElementById('btn-retake-photo');
const btnCloseWebcam = document.getElementById('btn-close-webcam');
const quickWebcamBtn = document.getElementById('quick-webcam-btn');
const navLinkWebcam = document.getElementById('nav-link-webcam');
const viewfinderStatusText = document.getElementById('viewfinder-status-text');

let webcamStream = null;
let isWebcamCaptured = false;

// ── State ─────────────────────────────────────────────────────
let selectedFile = null;
let currentEventSource = null;

// ── Pipeline Stage Definitions ────────────────────────────────
const STAGES = [
  { id: 'face_detection', label: 'Face Detect', icon: '🧠' },
  { id: 'image_upload', label: 'Upload', icon: '☁️' },
  { id: 'reverse_search', label: 'Search', icon: '🔍' },
  { id: 'blockchain', label: 'Blockchain', icon: '⛓️' },
  { id: 'verification', label: 'Verify', icon: '✅' },
];

// ── Upload Handling ───────────────────────────────────────────

uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
  uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    handleFile(files[0]);
  }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files.length > 0) {
    handleFile(fileInput.files[0]);
  }
});

function handleFile(file) {
  // Validate file type
  if (!file.type.startsWith('image/')) {
    showError('Please select an image file (JPEG, PNG, etc.)');
    return;
  }

  selectedFile = file;

  // Show preview
  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    previewName.textContent = file.name;
    previewSize.textContent = formatFileSize(file.size);
    uploadPreview.classList.add('visible');
  };
  reader.readAsDataURL(file);

  // Enable run button
  runBtn.disabled = false;

  // Hide previous results
  hideResults();
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ── Webcam Lifecycle & Capture ────────────────────────────────

async function startWebcam() {
  try {
    if (webcamStream) return;
    if (viewfinderStatusText) viewfinderStatusText.textContent = 'Connecting to camera…';

    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: 'user',
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });

    webcamStream = stream;
    if (webcamVideo) {
      webcamVideo.srcObject = stream;
      await webcamVideo.play();
    }
    if (viewfinderStatusText) viewfinderStatusText.textContent = 'Position face inside frame';
  } catch (err) {
    console.error('Webcam access error:', err);
    showError('Camera access denied or unavailable. Please grant camera permissions.');
    switchToUploadMode();
  }
}

function stopWebcam() {
  if (webcamStream) {
    webcamStream.getTracks().forEach((track) => track.stop());
    webcamStream = null;
  }
  if (webcamVideo) {
    webcamVideo.srcObject = null;
  }
  isWebcamCaptured = false;
}

function switchToWebcamMode() {
  if (tabWebcamMode) tabWebcamMode.classList.add('active');
  if (tabFileMode) tabFileMode.classList.remove('active');
  if (uploadZone) uploadZone.style.display = 'none';
  if (webcamZone) webcamZone.style.display = 'flex';
  if (btnRetakePhoto) btnRetakePhoto.style.display = 'none';
  if (btnCapturePhoto) btnCapturePhoto.style.display = 'inline-flex';
  startWebcam();
}

function switchToUploadMode() {
  if (tabFileMode) tabFileMode.classList.add('active');
  if (tabWebcamMode) tabWebcamMode.classList.remove('active');
  if (uploadZone) uploadZone.style.display = 'block';
  if (webcamZone) webcamZone.style.display = 'none';
  stopWebcam();
}

function captureWebcamPhoto() {
  if (!webcamVideo || !webcamStream) return;

  // Flash animation
  if (webcamFlash) {
    webcamFlash.classList.add('flash');
    setTimeout(() => webcamFlash.classList.remove('flash'), 180);
  }

  // Draw current video frame to canvas
  const canvas = webcamCanvas;
  canvas.width = webcamVideo.videoWidth || 640;
  canvas.height = webcamVideo.videoHeight || 480;
  const ctx = canvas.getContext('2d');

  // Flip horizontally to save naturally as seen in the mirrored selfie preview
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(webcamVideo, 0, 0, canvas.width, canvas.height);

  // Convert canvas to Blob / File
  canvas.toBlob((blob) => {
    if (!blob) {
      showError('Failed to capture frame from webcam');
      return;
    }

    const capturedFile = new File([blob], `webcam_face_${Date.now()}.jpg`, { type: 'image/jpeg' });
    handleFile(capturedFile);

    isWebcamCaptured = true;
    if (btnCapturePhoto) btnCapturePhoto.style.display = 'none';
    if (btnRetakePhoto) btnRetakePhoto.style.display = 'inline-flex';
    if (viewfinderStatusText) {
      viewfinderStatusText.textContent = '✓ Photo Captured! Ready to run pipeline.';
    }

    showToast('Photo captured successfully!');
  }, 'image/jpeg', 0.95);
}

function retakeWebcamPhoto() {
  isWebcamCaptured = false;
  if (btnCapturePhoto) btnCapturePhoto.style.display = 'inline-flex';
  if (btnRetakePhoto) btnRetakePhoto.style.display = 'none';
  if (viewfinderStatusText) {
    viewfinderStatusText.textContent = 'Position face inside frame';
  }
  if (uploadPreview) uploadPreview.classList.remove('visible');
  selectedFile = null;
  if (runBtn) runBtn.disabled = true;
  hideResults();
}

// ── Webcam Event Listeners ────────────────────────────────────
if (tabWebcamMode) {
  tabWebcamMode.addEventListener('click', switchToWebcamMode);
}
if (tabFileMode) {
  tabFileMode.addEventListener('click', switchToUploadMode);
}
if (quickWebcamBtn) {
  quickWebcamBtn.addEventListener('click', (e) => {
    e.preventDefault();
    switchToWebcamMode();
  });
}
if (btnCloseWebcam) {
  btnCloseWebcam.addEventListener('click', switchToUploadMode);
}
if (btnCapturePhoto) {
  btnCapturePhoto.addEventListener('click', captureWebcamPhoto);
}
if (btnRetakePhoto) {
  btnRetakePhoto.addEventListener('click', retakeWebcamPhoto);
}
if (navLinkWebcam) {
  navLinkWebcam.addEventListener('click', (e) => {
    e.preventDefault();
    const section = document.getElementById('upload-section');
    if (section) {
      section.scrollIntoView({ behavior: 'smooth' });
    }
    switchToWebcamMode();
  });
}

// ── Run Pipeline ──────────────────────────────────────────────

runBtn.addEventListener('click', () => {
  if (!selectedFile) return;
  runPipeline();
});

async function runPipeline() {
  // Reset UI
  hideResults();
  hideError();
  showPipeline();
  resetSteps();
  updateProgressBar(8, 'Initializing FaceChain Pipeline…');

  // Disable button
  runBtn.disabled = true;
  runBtn.classList.add('loading');

  // Upload the file first
  const formData = new FormData();
  formData.append('image', selectedFile);
  formData.append('model', modelSelect.value);

  try {
    // POST the image and get a run_id
    const response = await fetch('/api/run', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || 'Failed to start pipeline');
    }

    const { run_id } = await response.json();

    // Open SSE stream for progress
    connectSSE(run_id);
  } catch (err) {
    showError(err.message);
    runBtn.disabled = false;
    runBtn.classList.remove('loading');
  }
}

// ── SSE Progress Stream ───────────────────────────────────────

function connectSSE(runId) {
  if (currentEventSource) {
    currentEventSource.close();
  }

  let pipelineFinished = false;

  const es = new EventSource(`/api/progress/${runId}`);
  currentEventSource = es;

  es.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data);
    handleProgressEvent(data);
  });

  es.addEventListener('result', (e) => {
    pipelineFinished = true;
    const data = JSON.parse(e.data);
    handleResultEvent(data);
    es.close();
    currentEventSource = null;
  });

  es.addEventListener('error_event', (e) => {
    pipelineFinished = true;
    const data = JSON.parse(e.data);
    handlePipelineError(data);
    es.close();
    currentEventSource = null;
  });

  es.onerror = () => {
    if (pipelineFinished) {
      // Normal close after result/error was received
      es.close();
      currentEventSource = null;
      return;
    }

    // Connection dropped unexpectedly — EventSource auto-reconnects by default,
    // so only close if readyState is CLOSED (server ended the stream)
    if (es.readyState === EventSource.CLOSED) {
      es.close();
      currentEventSource = null;
      runBtn.disabled = false;
      runBtn.classList.remove('loading');
      // Don't show error — the pipeline may still be running on the server;
      // the results will be available via /api/results/<run_id>
      // Try to fetch results after a short delay
      setTimeout(() => fetchFinalResults(runId), 2000);
    }
    // If readyState is CONNECTING, EventSource is auto-reconnecting — let it retry
  };
}

// ── Progress Event Handlers ───────────────────────────────────

function handleProgressEvent(data) {
  const { stage, status } = data;

  const stepEl = document.getElementById(`step-${stage}`);
  if (!stepEl) return;

  // Remove all state classes
  stepEl.classList.remove('pending', 'running', 'done', 'error', 'skipped', 'active', 'completed');
  stepEl.classList.add(status);

  // Update status text
  const statusEl = stepEl.querySelector('.pipeline-step__status');
  if (status === 'running') {
    statusEl.textContent = data.data?.message || 'Processing…';
  } else if (status === 'done') {
    statusEl.textContent = getStepDoneText(stage, data.data);
  } else if (status === 'error') {
    statusEl.textContent = 'Failed';
  } else if (status === 'skipped') {
    statusEl.textContent = data.data?.reason || 'Skipped';
  }

  // Update overall progress bar
  const STAGE_PROGRESS = {
    face_detection: { running: 15, done: 25 },
    image_upload: { running: 35, done: 50 },
    reverse_search: { running: 60, done: 75 },
    blockchain: { running: 85, done: 92 },
    verification: { running: 96, done: 100 },
  };

  const percent = STAGE_PROGRESS[stage]?.[status];
  if (percent !== undefined) {
    const stageTitles = {
      face_detection: 'Face Detection',
      image_upload: 'Cloud Upload',
      reverse_search: 'Google Lens Search',
      blockchain: 'Sepolia Blockchain',
      verification: 'On-Chain Verification',
    };
    const title = stageTitles[stage] || stage;
    const label = status === 'running'
      ? `${title} in progress…`
      : status === 'done'
        ? `${title} complete ✓`
        : status === 'error'
          ? `${title} failed`
          : `${title} skipped`;
    updateProgressBar(percent, label);
  }
}

function getStepDoneText(stage, data) {
  switch (stage) {
    case 'face_detection':
      return `${data?.num_faces || 0} face(s), ${data?.encoding_dims || 128}-d`;
    case 'image_upload':
      return 'Uploaded ✓';
    case 'reverse_search':
      return `${data?.total_matches || 0} matches found`;
    case 'blockchain':
      if (data?.already_registered) {
        return 'Already on-chain ✓';
      }
      return `Block #${data?.block || '?'}`;
    case 'verification':
      return data?.verified ? 'Verified ✓' : 'Check complete';
    default:
      return 'Done';
  }
}

function handleResultEvent(data) {
  runBtn.disabled = false;
  runBtn.classList.remove('loading');

  updateProgressBar(100, 'All 5 Stages Verified Successfully ✓');

  // Render results
  renderResults(data);
  renderMatches(data);
  renderSummary(data);
}

function handlePipelineError(data) {
  runBtn.disabled = false;
  runBtn.classList.remove('loading');

  showError(data.error || 'Pipeline failed');

  // Still render any partial results we may have
  if (data.partial_results) {
    renderResults(data.partial_results);
  }
}

async function fetchFinalResults(runId) {
  // Poll for results if the SSE stream dropped during a long operation
  for (let attempt = 0; attempt < 30; attempt++) {
    try {
      const resp = await fetch(`/api/results/${runId}`);
      if (resp.ok) {
        const data = await resp.json();
        handleResultEvent(data);
        // Update all steps to done
        ['face_detection', 'image_upload', 'reverse_search', 'blockchain', 'verification'].forEach(stage => {
          const stageData = data.stages?.[stage];
          if (stageData) {
            handleProgressEvent({
              stage,
              status: stageData.skipped ? 'skipped' : 'done',
              data: stageData,
            });
          }
        });
        return;
      }
    } catch { /* ignore fetch errors */ }
    // Wait 2 seconds before retrying
    await new Promise(r => setTimeout(r, 2000));
  }
  // After 60s of polling, give up
  showError('Pipeline is taking too long. Check the terminal for details.');
  runBtn.disabled = false;
  runBtn.classList.remove('loading');
}

// ── Pipeline UI ───────────────────────────────────────────────

function updateProgressBar(percent, statusText) {
  const fill = document.getElementById('pipeline-progress-fill');
  const percentEl = document.getElementById('pipeline-progress-percent');
  const statusEl = document.getElementById('pipeline-progress-status');

  if (fill) {
    fill.style.width = `${percent}%`;
    if (percent > 0 && percent < 100) {
      fill.classList.add('active');
    } else {
      fill.classList.remove('active');
    }
  }
  if (percentEl) percentEl.textContent = `${percent}%`;
  if (statusEl && statusText) statusEl.textContent = statusText;
}

function showPipeline() {
  pipelineSection.classList.add('visible');
}

function resetSteps() {
  updateProgressBar(0, 'Ready to start');
  STAGES.forEach((s) => {
    const el = document.getElementById(`step-${s.id}`);
    if (el) {
      el.classList.remove('running', 'done', 'error', 'skipped', 'active', 'completed');
      el.classList.add('pending');
      const status = el.querySelector('.pipeline-step__status');
      if (status) status.textContent = 'Waiting…';
    }
  });
}

// ── Results Rendering ─────────────────────────────────────────

function renderResults(data) {
  const stages = data.stages || {};

  // Face detection card
  const fd = stages.face_detection || {};
  setResultValue('fd-faces', fd.num_faces ?? '—');
  setResultValue('fd-encoding', fd.encoding_dims ? `${fd.encoding_dims}-d vector` : '—');
  setResultValue('fd-location', fd.face_location
    ? `x:${fd.face_location.x} y:${fd.face_location.y} ${fd.face_location.w}×${fd.face_location.h}`
    : '—');

  // Show cropped face if available
  const cropImg = document.getElementById('crop-img');
  if (fd.cropped_path && cropImg) {
    cropImg.src = `/uploads/crop`;
    cropImg.style.display = 'block';
  }

  // Image upload card
  const iu = stages.image_upload || {};
  const uploadUrlEl = document.getElementById('iu-url');
  if (iu.public_url) {
    uploadUrlEl.innerHTML = `<a href="${iu.public_url}" target="_blank" rel="noopener">${truncate(iu.public_url, 45)}</a>`;
  } else {
    uploadUrlEl.textContent = '—';
  }

  // Reverse search card
  const rs = stages.reverse_search || {};
  setResultValue('rs-title', rs.title || '—');
  const rsLinkEl = document.getElementById('rs-link');
  if (rs.link) {
    rsLinkEl.innerHTML = `<a href="${rs.link}" target="_blank" rel="noopener">${truncate(rs.link, 40)}</a>`;
  } else {
    rsLinkEl.textContent = '—';
  }
  setResultValue('rs-source', rs.source || '—');

  const rsBadge = document.getElementById('rs-badge');
  if (rs.is_social_media) {
    rsBadge.innerHTML = '<span class="badge badge-social">🟢 Social Media</span>';
  } else if (rs.source) {
    rsBadge.innerHTML = '<span class="badge badge-web">🟡 Web</span>';
  } else {
    rsBadge.innerHTML = '';
  }

  setResultValue('rs-matches', rs.total_matches ?? '—');

  // Blockchain card
  const bc = stages.blockchain || {};
  if (bc.skipped) {
    setResultValue('bc-status', '⚠ Skipped — ' + (bc.reason || ''));
    setResultValue('bc-block', '—');
    setResultValue('bc-gas', '—');
    setResultValue('bc-tx', '—');
    document.getElementById('bc-etherscan-link')?.setAttribute('style', 'display:none');
  } else if (bc.already_registered) {
    setResultValue('bc-status', 'Already Registered On-Chain ✓');
    setResultValue('bc-block', 'Previously Mined');
    setResultValue('bc-gas', '0 (Existing)');

    const txEl = document.getElementById('bc-tx');
    if (txEl) txEl.textContent = 'Existing On-Chain Record';

    const ethLink = document.getElementById('bc-etherscan-link');
    if (bc.etherscan && ethLink) {
      ethLink.href = bc.etherscan;
      ethLink.textContent = 'View Contract on Sepolia ↗';
      ethLink.style.display = 'inline-flex';
    }

    // Data hash
    const hashEl = document.getElementById('bc-hash');
    if (bc.data_hash && hashEl) {
      hashEl.innerHTML = `<span>${truncate('0x' + bc.data_hash, 22)}</span>
        <button class="copy-btn" onclick="copyText('0x${bc.data_hash}')" title="Copy">📋</button>`;
    }
  } else {
    setResultValue('bc-status', 'Confirmed ✓');
    setResultValue('bc-block', bc.block ?? '—');
    setResultValue('bc-gas', bc.gas_used ?? '—');

    const txEl = document.getElementById('bc-tx');
    if (bc.tx_hash) {
      txEl.innerHTML = `<span>${truncate('0x' + bc.tx_hash, 22)}</span>
        <button class="copy-btn" onclick="copyText('0x${bc.tx_hash}')" title="Copy">📋</button>`;
    }

    const ethLink = document.getElementById('bc-etherscan-link');
    if (bc.etherscan && ethLink) {
      ethLink.href = bc.etherscan;
      ethLink.style.display = 'inline-flex';
    }

    // Data hash
    const hashEl = document.getElementById('bc-hash');
    if (bc.data_hash && hashEl) {
      hashEl.innerHTML = `<span>${truncate('0x' + bc.data_hash, 22)}</span>
        <button class="copy-btn" onclick="copyText('0x${bc.data_hash}')" title="Copy">📋</button>`;
    }
  }

  // Verification card
  const vf = stages.verification || {};
  const vfBadge = document.getElementById('vf-badge');
  if (vf.skipped) {
    vfBadge.innerHTML = '<span class="badge badge-skipped">⚠ Skipped</span>';
    setResultValue('vf-registrant', '—');
    setResultValue('vf-timestamp', '—');
  } else if (vf.verified) {
    vfBadge.innerHTML = '<span class="badge badge-verified">✓ Verified</span>';
    setResultValue('vf-registrant', vf.registrant ? truncate(vf.registrant, 20) : '—');
    setResultValue('vf-timestamp', vf.timestamp ? new Date(vf.timestamp * 1000).toLocaleString() : '—');
  } else {
    vfBadge.innerHTML = '<span class="badge badge-failed">✗ Failed</span>';
    setResultValue('vf-registrant', '—');
    setResultValue('vf-timestamp', '—');
  }

  resultsSection.classList.add('visible');
}

function renderMatches(data) {
  const rs = data.stages?.reverse_search || {};
  const allMatches = rs.all_matches || [];

  if (allMatches.length === 0) {
    matchesSection.classList.remove('visible');
    return;
  }

  const countEl = document.getElementById('matches-total');
  const socialCount = allMatches.filter(m => isSocialDomain(m.link || m.source)).length;
  const webCount = allMatches.length - socialCount;

  countEl.innerHTML = `<strong>${allMatches.length}</strong> matches found · <strong>${socialCount}</strong> social · <strong>${webCount}</strong> web`;

  // Render cards
  const grid = document.getElementById('matches-grid');
  grid.innerHTML = '';

  allMatches.forEach((match, i) => {
    const isSocial = isSocialDomain(match.link || match.source);
    const card = document.createElement('div');
    card.className = 'match-card';
    card.dataset.type = isSocial ? 'social' : 'web';
    card.style.animationDelay = `${i * 50}ms`;
    card.style.animation = 'fadeSlideIn 0.4s ease-out both';

    const thumbHtml = match.thumbnail
      ? `<img src="${match.thumbnail}" alt="${escapeHtml(match.title || '')}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\'match-card__thumb-placeholder\\'>🖼️</div>'">`
      : `<div class="match-card__thumb-placeholder">🖼️</div>`;

    const badgeHtml = isSocial
      ? '<span class="badge badge-social">Social</span>'
      : '<span class="badge badge-web">Web</span>';

    card.innerHTML = `
      <div class="match-card__thumb">
        ${thumbHtml}
        <div class="match-card__badge">${badgeHtml}</div>
      </div>
      <div class="match-card__body">
        <div class="match-card__title">${escapeHtml(match.title || 'Untitled')}</div>
        <div class="match-card__source">${escapeHtml(match.source || getDomain(match.link))}</div>
        ${match.link ? `<a class="match-card__link" href="${match.link}" target="_blank" rel="noopener">View source →</a>` : ''}
      </div>
    `;

    grid.appendChild(card);
  });

  matchesSection.classList.add('visible');

  // Set up filter buttons
  setupFilters();
}

function renderSummary(data) {
  const el = document.getElementById('summary-time');
  if (el) el.textContent = `${data.elapsed_seconds ?? '?'}s`;

  const tsEl = document.getElementById('summary-timestamp');
  if (tsEl) tsEl.textContent = data.timestamp ? new Date(data.timestamp).toLocaleString() : '—';

  summaryBar.classList.add('visible');
}

// ── Match Filtering ───────────────────────────────────────────

function setupFilters() {
  const btns = document.querySelectorAll('.filter-btn');
  btns.forEach(btn => {
    btn.addEventListener('click', () => {
      btns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      filterMatches(btn.dataset.filter);
    });
  });
}

function filterMatches(filter) {
  const cards = document.querySelectorAll('.match-card');
  cards.forEach(card => {
    if (filter === 'all') {
      card.style.display = '';
    } else {
      card.style.display = card.dataset.type === filter ? '' : 'none';
    }
  });
}

// ── Utilities ─────────────────────────────────────────────────

function setResultValue(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function truncate(str, max) {
  if (!str) return '';
  return str.length > max ? str.substring(0, max) + '…' : str;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function getDomain(url) {
  try {
    return new URL(url).hostname.replace('www.', '');
  } catch {
    return url || '';
  }
}

const SOCIAL_DOMAINS = [
  'instagram.com', 'twitter.com', 'x.com', 'facebook.com',
  'linkedin.com', 'pinterest.com', 'tiktok.com', 'reddit.com',
  'tumblr.com', 'flickr.com', 'youtube.com', 'threads.net', 'vk.com',
];

function isSocialDomain(url) {
  if (!url) return false;
  const lower = url.toLowerCase();
  return SOCIAL_DOMAINS.some(d => lower.includes(d));
}

function hideResults() {
  resultsSection.classList.remove('visible');
  matchesSection.classList.remove('visible');
  summaryBar.classList.remove('visible');
  // pipelineSection remains visible so user can see stages
}

function showError(msg) {
  errorText.textContent = msg;
  errorBanner.classList.add('visible');
}

function hideError() {
  errorBanner.classList.remove('visible');
}

// ── Copy to Clipboard ─────────────────────────────────────────

function copyText(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied to clipboard');
  }).catch(() => {
    // Fallback
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast('Copied to clipboard');
  });
}

function showToast(message) {
  // Remove existing toast
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span>✓</span> ${message}`;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('hiding');
    setTimeout(() => toast.remove(), 300);
  }, 2000);
}

// ── Top Navigation Action Buttons ─────────────────────────────

// 1. Shield: Scroll to Verification Pipeline and pulse
const navBtnVerify = document.getElementById('nav-btn-verify');
if (navBtnVerify) {
  navBtnVerify.addEventListener('click', (e) => {
    e.preventDefault();
    const target = document.getElementById('pipeline-section');
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      target.classList.add('highlight-pulse');
      setTimeout(() => target.classList.remove('highlight-pulse'), 1500);
    }
  });
}

// 2. Phone: Open Contact & Support Modal
const navBtnPhone = document.getElementById('nav-btn-phone');
const contactModal = document.getElementById('contact-modal');
const contactModalClose = document.getElementById('contact-modal-close');
const contactModalBackdrop = document.getElementById('contact-modal-backdrop');

if (navBtnPhone && contactModal) {
  navBtnPhone.addEventListener('click', () => {
    contactModal.classList.add('visible');
    contactModal.setAttribute('aria-hidden', 'false');
  });
}

if (contactModalClose) {
  contactModalClose.addEventListener('click', () => {
    contactModal.classList.remove('visible');
    contactModal.setAttribute('aria-hidden', 'true');
  });
}

if (contactModalBackdrop) {
  contactModalBackdrop.addEventListener('click', () => {
    contactModal.classList.remove('visible');
    contactModal.setAttribute('aria-hidden', 'true');
  });
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && contactModal && contactModal.classList.contains('visible')) {
    contactModal.classList.remove('visible');
    contactModal.setAttribute('aria-hidden', 'true');
  }
});

// 4. Share: Share link via Web Share API or copy URL
const navBtnShare = document.getElementById('nav-btn-share');
if (navBtnShare) {
  navBtnShare.addEventListener('click', async () => {
    const shareData = {
      title: 'FaceChain — Biometric Verification Pipeline',
      text: 'FaceChain: AI facial recognition, Google Lens reverse search, and Ethereum Sepolia verification.',
      url: window.location.href,
    };

    if (navigator.share) {
      try {
        await navigator.share(shareData);
        return;
      } catch (err) {
        if (err.name !== 'AbortError') {
          copyText(window.location.href);
          showToast('FaceChain link copied to clipboard!');
        }
      }
    } else {
      copyText(window.location.href);
      showToast('FaceChain link copied to clipboard!');
    }
  });
}

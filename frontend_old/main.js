/**
 * Lead Autopilot — Frontend Logic
 *
 * Handles form validation, API submission, status polling,
 * and UI state transitions.
 */

// ── Configuration ───────────────────────────────────────────

const API_BASE = '/api';
const POLL_INTERVAL = 2000; // ms between status polls

// ── DOM Elements ────────────────────────────────────────────

const form = document.getElementById('lead-form');
const submitBtn = document.getElementById('submit-btn');
const formSection = document.getElementById('form-section');
const processingSection = document.getElementById('processing-section');
const successSection = document.getElementById('success-section');
const errorSection = document.getElementById('error-section');
const processingTitle = document.getElementById('processing-title');
const processingSubtitle = document.getElementById('processing-subtitle');
const successMessage = document.getElementById('success-message');
const errorMessage = document.getElementById('error-message');
const downloadPdfBtn = document.getElementById('download-pdf-btn');
const pipelineSteps = document.getElementById('pipeline-steps');

// ── Validation ──────────────────────────────────────────────

const validators = {
  name: (value) => {
    if (!value.trim()) return 'Full name is required';
    if (value.trim().length < 2) return 'Name must be at least 2 characters';
    return '';
  },
  email: (value) => {
    if (!value.trim()) return 'Email is required';
    const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRe.test(value)) return 'Please enter a valid email address';
    return '';
  },
  company: (value) => {
    if (!value.trim()) return 'Company name is required';
    return '';
  },
  website: (value) => {
    if (!value.trim()) return 'Company website is required';
    // Allow with or without protocol
    let url = value.trim();
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'https://' + url;
    }
    try {
      new URL(url);
      return '';
    } catch {
      return 'Please enter a valid URL (e.g., https://example.com)';
    }
  },
};

function validateField(fieldId) {
  const input = document.getElementById(fieldId);
  const errorSpan = document.getElementById(`${fieldId}-error`);
  const validator = validators[fieldId];

  if (!validator || !input) return true;

  const error = validator(input.value);
  if (errorSpan) errorSpan.textContent = error;

  if (error) {
    input.classList.add('error');
    input.classList.remove('valid');
    return false;
  } else if (input.value.trim()) {
    input.classList.remove('error');
    input.classList.add('valid');
    return true;
  } else {
    input.classList.remove('error', 'valid');
    return true;
  }
}

function validateForm() {
  let isValid = true;
  for (const fieldId of Object.keys(validators)) {
    if (!validateField(fieldId)) isValid = false;
  }
  return isValid;
}

// Attach real-time validation
for (const fieldId of Object.keys(validators)) {
  const input = document.getElementById(fieldId);
  if (input) {
    input.addEventListener('blur', () => validateField(fieldId));
    input.addEventListener('input', () => {
      // Clear error on typing
      const errorSpan = document.getElementById(`${fieldId}-error`);
      if (errorSpan) errorSpan.textContent = '';
      input.classList.remove('error');
    });
  }
}

// ── Form Submission ─────────────────────────────────────────

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  if (!validateForm()) return;

  // Collect form data
  let website = document.getElementById('website').value.trim();
  if (!website.startsWith('http://') && !website.startsWith('https://')) {
    website = 'https://' + website;
  }

  const payload = {
    name: document.getElementById('name').value.trim(),
    email: document.getElementById('email').value.trim(),
    company: document.getElementById('company').value.trim(),
    website: website,
    industry: document.getElementById('industry').value,
    company_size: document.getElementById('company_size').value,
    message: document.getElementById('message').value.trim(),
  };

  // Disable button
  submitBtn.disabled = true;
  submitBtn.classList.add('loading');

  try {
    const response = await fetch(`${API_BASE}/leads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Server error (${response.status})`);
    }

    const data = await response.json();
    const leadId = data.lead_id;

    // Switch to processing view
    showSection('processing');
    startStatusPolling(leadId, payload.email);

  } catch (err) {
    console.error('Submission error:', err);
    showError(err.message || 'Failed to submit. Please check your connection and try again.');
    submitBtn.disabled = false;
    submitBtn.classList.remove('loading');
  }
});

// ── Status Polling ──────────────────────────────────────────

const STEP_ORDER = ['submitted', 'validating', 'enriching', 'generating_pdf', 'sending_email', 'complete'];

const STEP_MESSAGES = {
  submitted: 'Your information has been received',
  validating: 'Checking your details...',
  enriching: 'Analyzing your company website with AI...',
  generating_pdf: 'Creating your personalized report...',
  sending_email: 'Delivering the report to your inbox...',
  logging: 'Finalizing...',
  complete: 'All done!',
};

function updatePipelineUI(currentStep, completedSteps) {
  const steps = pipelineSteps.querySelectorAll('.pipeline-step');

  steps.forEach((stepEl) => {
    const stepName = stepEl.dataset.step;
    stepEl.classList.remove('completed', 'active', 'error');

    if (completedSteps.includes(stepName)) {
      stepEl.classList.add('completed');
      const statusEl = stepEl.querySelector('.step-status');
      if (statusEl) statusEl.textContent = '✓';
    } else if (stepName === currentStep) {
      stepEl.classList.add('active');
    }
  });

  // Update subtitle
  const message = STEP_MESSAGES[currentStep] || 'Processing...';
  processingSubtitle.textContent = message;
}

function startStatusPolling(leadId, email) {
  let pollCount = 0;
  const maxPolls = 120; // 4 minutes max

  const poll = async () => {
    pollCount++;
    if (pollCount > maxPolls) {
      showError('Processing is taking longer than expected. Your report may still arrive by email.');
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/leads/${leadId}/status`);
      if (!response.ok) throw new Error('Status check failed');

      const data = await response.json();

      updatePipelineUI(data.current_step, data.steps_completed);

      if (data.is_complete) {
        if (data.current_step === 'complete') {
          // Success!
          showSuccess(leadId, email);
        } else if (data.current_step === 'error') {
          showError(data.error_message || 'An error occurred during processing.');
        }
        return;
      }

      // Continue polling
      setTimeout(poll, POLL_INTERVAL);

    } catch (err) {
      console.error('Polling error:', err);
      // Retry a few times before giving up
      if (pollCount < maxPolls) {
        setTimeout(poll, POLL_INTERVAL * 2);
      } else {
        showError('Lost connection to the server. Your report may still arrive by email.');
      }
    }
  };

  // Start polling after a short delay
  setTimeout(poll, 1000);
}

// ── UI State Management ─────────────────────────────────────

function showSection(sectionName) {
  formSection.classList.add('hidden');
  processingSection.classList.add('hidden');
  successSection.classList.add('hidden');
  errorSection.classList.add('hidden');

  // Also hide hero during processing/success/error
  const hero = document.getElementById('hero');

  switch (sectionName) {
    case 'form':
      formSection.classList.remove('hidden');
      hero.classList.remove('hidden');
      break;
    case 'processing':
      processingSection.classList.remove('hidden');
      hero.classList.add('hidden');
      break;
    case 'success':
      successSection.classList.remove('hidden');
      hero.classList.add('hidden');
      break;
    case 'error':
      errorSection.classList.remove('hidden');
      hero.classList.add('hidden');
      break;
  }

  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showSuccess(leadId, email) {
  successMessage.textContent = `Your personalized business intelligence report has been sent to ${email}. Check your inbox!`;

  // Show download button
  downloadPdfBtn.href = `${API_BASE}/leads/${leadId}/pdf`;
  downloadPdfBtn.classList.remove('hidden');
  downloadPdfBtn.setAttribute('download', '');

  showSection('success');
}

function showError(message) {
  errorMessage.textContent = message;
  showSection('error');
}

// ── Reset Form (called by "Submit Another" button) ──────────

window.resetForm = function () {
  form.reset();
  submitBtn.disabled = false;
  submitBtn.classList.remove('loading');

  // Clear validation states
  form.querySelectorAll('.form-input').forEach((input) => {
    input.classList.remove('error', 'valid');
  });
  form.querySelectorAll('.form-error').forEach((span) => {
    span.textContent = '';
  });

  // Reset pipeline steps
  pipelineSteps.querySelectorAll('.pipeline-step').forEach((step) => {
    step.classList.remove('completed', 'active', 'error');
    const statusEl = step.querySelector('.step-status');
    if (statusEl) statusEl.textContent = '';
  });

  // Hide download button
  downloadPdfBtn.classList.add('hidden');

  showSection('form');
};

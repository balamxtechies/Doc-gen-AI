let selectedFiles = [];
let currentAnalysis = null;
let activeModalSlug = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  lucide.createIcons();
  setupDropzone();
  loadSettings();
  loadActiveApis();
});

// Tab Navigation
function switchTab(tab) {
  const tabs = ["studio", "hub", "settings"];
  tabs.forEach(t => {
    const el = document.getElementById(`tab-${t}`);
    const nav = document.getElementById(`nav-${t}`);
    if (t === tab) {
      el.classList.remove("hidden");
      nav.classList.add("bg-white", "text-indigo-600", "shadow-sm");
      nav.classList.remove("text-slate-700");
    } else {
      el.classList.add("hidden");
      nav.classList.remove("bg-white", "text-indigo-600", "shadow-sm");
      nav.classList.add("text-slate-700");
    }
  });

  if (tab === "hub") {
    loadActiveApis();
  } else if (tab === "settings") {
    loadSettings();
  }
}

// Drag & Drop File Handling
function setupDropzone() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");

  dropzone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (e) => {
    handleFiles(e.target.files);
  });

  ["dragenter", "dragover"].forEach(event => {
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      dropzone.classList.add("border-indigo-500", "bg-indigo-50/70");
    });
  });

  ["dragleave", "drop"].forEach(event => {
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      dropzone.classList.remove("border-indigo-500", "bg-indigo-50/70");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    handleFiles(e.dataTransfer.files);
  });
}

function handleFiles(files) {
  for (let i = 0; i < files.length; i++) {
    selectedFiles.push(files[i]);
  }
  renderSelectedFiles();
}

function renderSelectedFiles() {
  const container = document.getElementById("selected-files-container");
  if (selectedFiles.length === 0) {
    container.classList.add("hidden");
    container.innerHTML = "";
    return;
  }

  container.classList.remove("hidden");
  container.innerHTML = selectedFiles.map((f, idx) => `
    <div class="flex items-center justify-between bg-white px-3 py-2 rounded-xl border border-slate-200 text-xs shadow-xs">
      <div class="flex items-center space-x-2 truncate">
        <i data-lucide="file-text" class="w-4 h-4 text-indigo-500 shrink-0"></i>
        <span class="font-medium text-slate-700 truncate">${f.name}</span>
        <span class="text-slate-400">(${(f.size / 1024).toFixed(1)} KB)</span>
      </div>
      <button type="button" onclick="removeFile(${idx})" class="text-slate-400 hover:text-red-500 transition">
        <i data-lucide="x" class="w-3.5 h-3.5"></i>
      </button>
    </div>
  `).join("");
  lucide.createIcons();
}

function removeFile(index) {
  selectedFiles.splice(index, 1);
  renderSelectedFiles();
}

// Prompt Preset Shortcuts
function setPromptPreset(preset) {
  const nameInput = document.getElementById("input-doc-name");
  const promptInput = document.getElementById("input-prompt");

  if (preset === "invoice") {
    nameInput.value = "Vendor Invoice";
    promptInput.value = "Extract Invoice Number, Invoice Date, Due Date, Vendor Name, Vendor Address, Customer Name, Line Items table (Description, Quantity, Unit Price, Total Amount), Tax Amount, and Grand Total.";
  } else if (preset === "id_card") {
    nameInput.value = "Identity Card";
    promptInput.value = "Extract Full Name, Father's Name, Date of Birth (DD-MM-YYYY), Identification Number, Gender, Issue Date, and Expiry Date.";
  } else if (preset === "receipt") {
    nameInput.value = "Retail Receipt";
    promptInput.value = "Extract Store Name, Store Address, Transaction Date, Receipt Number, Items List (Item Name, Price), Subtotal, Tax, and Total Amount Paid.";
  } else if (preset === "payslip") {
    nameInput.value = "Salary Payslip";
    promptInput.value = "Extract Employee Name, Employee ID, Company Name, Pay Period / Month, Basic Salary, Allowances list, Deductions list, and Net Payable Salary.";
  }
}

// Step 1: AI Analysis
async function startAnalysis() {
  const name = document.getElementById("input-doc-name").value.trim();
  const prompt = document.getElementById("input-prompt").value.trim();

  if (!name) {
    alert("Please enter a Document Type Name (e.g. Vendor Invoice).");
    return;
  }
  if (!prompt) {
    alert("Please provide extraction requirements (what fields you need).");
    return;
  }
  if (selectedFiles.length === 0) {
    alert("Please upload at least one sample document (PDF or image).");
    return;
  }

  // Switch panels
  document.getElementById("panel-idle").classList.add("hidden");
  document.getElementById("panel-results").classList.add("hidden");
  document.getElementById("panel-published-success").classList.add("hidden");
  document.getElementById("panel-loading").classList.remove("hidden");
  document.getElementById("btn-analyze").disabled = true;

  const formData = new FormData();
  formData.append("name", name);
  formData.append("prompt", prompt);
  selectedFiles.forEach(file => {
    formData.append("files", file);
  });

  try {
    const res = await fetch("/api/v1/admin/analyze", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Analysis failed.");
    }

    currentAnalysis = data;
    renderAnalysisResults(data);
  } catch (err) {
    alert("Error: " + err.message);
    document.getElementById("panel-idle").classList.remove("hidden");
  } finally {
    document.getElementById("panel-loading").classList.add("hidden");
    document.getElementById("btn-analyze").disabled = false;
  }
}

function renderAnalysisResults(data) {
  document.getElementById("panel-results").classList.remove("hidden");
  document.getElementById("res-display-name").textContent = data.display_name || data.name || "Custom Document";
  document.getElementById("res-summary").textContent = data.document_summary || "";
  document.getElementById("res-timing-badge").textContent = `${data.processing_time_ms || 0} ms (${data.total_pages_analyzed || 1} pages)`;
  document.getElementById("res-slug").value = data.suggested_slug || "custom_doc";

  // Render fields table
  const fields = data.fields || [];
  document.getElementById("res-field-count").textContent = fields.length;
  const tbody = document.getElementById("res-fields-tbody");
  tbody.innerHTML = fields.map(f => `
    <tr class="hover:bg-slate-50">
      <td class="py-2 px-3 font-mono text-indigo-700 font-semibold">${f.key}</td>
      <td class="py-2 px-3 font-medium text-slate-800">${f.label || f.key}</td>
      <td class="py-2 px-3">
        <span class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${getTypeBadgeClass(f.type)}">${f.type}</span>
      </td>
      <td class="py-2 px-3 text-slate-500">${f.description || ""}</td>
    </tr>
  `).join("");

  // Render JSON Preview
  const preview = data.preview_extraction || {};
  document.getElementById("res-json-preview").textContent = JSON.stringify(preview, null, 2);

  // Render Generated Python Code
  const codeEl = document.getElementById("res-code-preview");
  if (codeEl) {
    codeEl.textContent = data.python_code || "# No code generated";
  }

  lucide.createIcons();
}

function showPreviewTab(tab) {
  const jsonTab = document.getElementById("preview-tab-json");
  const codeTab = document.getElementById("preview-tab-code");
  const jsonBtn = document.getElementById("tab-btn-preview");
  const codeBtn = document.getElementById("tab-btn-code");

  if (tab === "json") {
    jsonTab.classList.remove("hidden");
    codeTab.classList.add("hidden");
    jsonBtn.className = "text-xs font-bold px-3 py-1 rounded-lg bg-indigo-50 text-indigo-700 transition";
    codeBtn.className = "text-xs font-bold px-3 py-1 rounded-lg text-slate-500 hover:text-slate-800 transition";
  } else {
    jsonTab.classList.add("hidden");
    codeTab.classList.remove("hidden");
    jsonBtn.className = "text-xs font-bold px-3 py-1 rounded-lg text-slate-500 hover:text-slate-800 transition";
    codeBtn.className = "text-xs font-bold px-3 py-1 rounded-lg bg-indigo-50 text-indigo-700 transition";
  }
}

function copyCodePreview() {
  const code = document.getElementById("res-code-preview").textContent;
  navigator.clipboard.writeText(code);
  alert("Generated Python extractor code copied to clipboard!");
}

function getTypeBadgeClass(type) {
  switch ((type || "").toLowerCase()) {
    case "string": return "bg-blue-50 text-blue-700 border border-blue-200";
    case "number": return "bg-emerald-50 text-emerald-700 border border-emerald-200";
    case "date": return "bg-amber-50 text-amber-700 border border-amber-200";
    case "array": return "bg-purple-50 text-purple-700 border border-purple-200";
    case "boolean": return "bg-rose-50 text-rose-700 border border-rose-200";
    default: return "bg-slate-100 text-slate-700";
  }
}

// Step 2: Publish API
async function publishAPI() {
  if (!currentAnalysis) return;

  const btn = document.getElementById("btn-publish");
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Generating Zero-AI Microservice...</span>`;
  lucide.createIcons();

  const slug = document.getElementById("res-slug").value.trim();
  const name = document.getElementById("input-doc-name").value.trim();
  const prompt = document.getElementById("input-prompt").value.trim();

  const payload = {
    name: name,
    slug: slug,
    description: currentAnalysis.document_summary || "",
    prompt: prompt,
    fields: currentAnalysis.fields || [],
    json_schema: currentAnalysis.json_schema || {},
    runtime_system_prompt: currentAnalysis.runtime_system_prompt || "",
    python_code: currentAnalysis.python_code || "",
    sample_output: currentAnalysis.preview_extraction || {}
  };

  try {
    const res = await fetch("/api/v1/admin/publish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Publishing failed.");
    }

    // Success UI
    document.getElementById("panel-results").classList.add("hidden");
    document.getElementById("panel-published-success").classList.remove("hidden");
    document.getElementById("pub-standalone-url").value = data.standalone_url;
    document.getElementById("pub-service-dir").value = data.service_dir;
    document.getElementById("pub-curl-snippet").textContent = data.curl_example;

    loadActiveApis();
  } catch (err) {
    alert("Error publishing API: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="cpu" class="w-4 h-4"></i><span>Deploy Standalone Zero-AI Microservice</span>`;
    lucide.createIcons();
  }
}

function resetStudio() {
  selectedFiles = [];
  currentAnalysis = null;
  renderSelectedFiles();
  document.getElementById("input-doc-name").value = "";
  document.getElementById("input-prompt").value = "";
  document.getElementById("panel-published-success").classList.add("hidden");
  document.getElementById("panel-idle").classList.remove("hidden");
}

// Tab 2: Active APIs Hub
async function loadActiveApis() {
  try {
    const res = await fetch("/api/v1/admin/documents");
    const docs = await res.json();

    const countBadge = document.getElementById("badge-api-count");
    if (countBadge) countBadge.textContent = docs.length;

    const grid = document.getElementById("hub-cards-grid");
    const empty = document.getElementById("hub-empty-state");

    if (docs.length === 0) {
      grid.classList.add("hidden");
      empty.classList.remove("hidden");
      return;
    }

    empty.classList.add("hidden");
    grid.classList.remove("hidden");

    grid.innerHTML = docs.map(doc => `
      <div class="glass-card p-6 rounded-2xl shadow-sm hover:shadow-md transition flex flex-col justify-between space-y-4 border border-slate-200">
        <div>
          <div class="flex items-start justify-between">
            <div>
              <h3 class="font-bold text-slate-900 text-base">${doc.name}</h3>
              <span class="text-xs font-mono text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md mt-1 inline-block">/api/v1/extract/${doc.slug}</span>
            </div>
            <span class="text-[10px] font-bold bg-slate-100 text-slate-600 px-2 py-1 rounded-full">
              ${doc.call_count || 0} calls
            </span>
          </div>
          <p class="text-xs text-slate-500 mt-2 line-clamp-2">${doc.description || doc.prompt || "Custom document extraction API"}</p>
        </div>

        <div class="space-y-2 pt-2 border-t border-slate-100">
          <div class="flex items-center space-x-2">
            <button onclick="openTestModal('${doc.slug}', '${doc.name}')" class="flex-1 py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs flex items-center justify-center space-x-1.5 transition">
              <i data-lucide="play" class="w-3.5 h-3.5"></i>
              <span>Test API</span>
            </button>
            <button onclick="copySnippet('${doc.endpoint_url}')" title="Copy Endpoint URL" class="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs transition">
              <i data-lucide="copy" class="w-4 h-4"></i>
            </button>
            <button onclick="deleteDocApi('${doc.slug}')" title="Delete API" class="p-2 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-600 text-xs transition">
              <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>
          </div>
        </div>
      </div>
    `).join("");

    lucide.createIcons();
  } catch (err) {
    console.error("Error loading active APIs:", err);
  }
}

async function deleteDocApi(slug) {
  if (!confirm(`Are you sure you want to deactivate and delete the API endpoint for '${slug}'?`)) return;
  try {
    const res = await fetch(`/api/v1/admin/documents/${slug}`, { method: "DELETE" });
    if (res.ok) {
      loadActiveApis();
    } else {
      alert("Failed to delete document API.");
    }
  } catch (err) {
    alert("Error deleting API: " + err.message);
  }
}

// Interactive Test Modal
function openTestModal(slug, name) {
  activeModalSlug = slug;
  document.getElementById("modal-title").textContent = `Test: ${name}`;
  document.getElementById("modal-slug").textContent = `POST /api/v1/extract/${slug}`;
  document.getElementById("modal-file-input").value = "";
  document.getElementById("modal-results-area").classList.add("hidden");
  document.getElementById("test-modal").classList.remove("hidden");
  lucide.createIcons();
}

function closeTestModal() {
  document.getElementById("test-modal").classList.add("hidden");
  activeModalSlug = null;
}

async function executeModalTest() {
  const fileInput = document.getElementById("modal-file-input");
  if (!fileInput.files || fileInput.files.length === 0) {
    alert("Please select a document file to test.");
    return;
  }

  const btn = document.getElementById("btn-modal-run");
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Extracting locally (Zero AI Calls)...</span>`;
  lucide.createIcons();

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const res = await fetch(`/api/v1/extract/${activeModalSlug}`, {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    document.getElementById("modal-results-area").classList.remove("hidden");
    document.getElementById("modal-timing").textContent = `${data.processing_time_ms || 0} ms (${data.page_count || 1} pages)`;
    document.getElementById("modal-json-output").textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    alert("Test execution error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="play" class="w-4 h-4"></i><span>Execute Live Extraction</span>`;
    lucide.createIcons();
  }
}

// Tab 3: Settings
async function loadSettings() {
  try {
    const res = await fetch("/api/v1/admin/settings");
    const data = await res.json();

    const badge = document.getElementById("status-key-badge");
    const text = document.getElementById("status-key-text");

    if (data.has_api_key) {
      badge.className = "flex items-center space-x-1.5 text-xs px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 cursor-pointer";
      text.textContent = `Gemini Ready (${data.masked_api_key})`;
    } else {
      badge.className = "flex items-center space-x-1.5 text-xs px-3 py-1.5 rounded-lg bg-amber-50 text-amber-700 border border-amber-200 cursor-pointer animate-pulse";
      text.textContent = "Gemini Key Required";
    }

    if (data.default_model) {
      document.getElementById("settings-model").value = data.default_model;
    }
  } catch (err) {
    console.error("Error loading settings:", err);
  }
}

async function saveSettings() {
  const key = document.getElementById("settings-api-key").value.trim();
  const model = document.getElementById("settings-model").value;
  const msg = document.getElementById("settings-msg");
  const btn = document.getElementById("btn-save-settings");

  if (!key) {
    msg.className = "text-xs p-3 rounded-xl bg-rose-50 text-rose-700 border border-rose-200";
    msg.textContent = "Please enter an API Key.";
    msg.classList.remove("hidden");
    return;
  }

  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Verifying with Google Gemini...</span>`;
  lucide.createIcons();

  try {
    const res = await fetch("/api/v1/admin/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: key, default_model: model })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Validation failed.");
    }

    msg.className = "text-xs p-3 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200";
    msg.textContent = data.message;
    msg.classList.remove("hidden");
    document.getElementById("settings-api-key").value = "";
    loadSettings();
  } catch (err) {
    msg.className = "text-xs p-3 rounded-xl bg-rose-50 text-rose-700 border border-rose-200";
    msg.textContent = err.message;
    msg.classList.remove("hidden");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="save" class="w-4 h-4"></i><span>Save & Verify API Key</span>`;
    lucide.createIcons();
  }
}

// Utilities
function copySnippet(text) {
  navigator.clipboard.writeText(text);
  alert("Endpoint URL copied to clipboard: " + text);
}

function copyToClipboard(elementId) {
  const copyText = document.getElementById(elementId);
  copyText.select();
  navigator.clipboard.writeText(copyText.value);
  alert("Copied to clipboard!");
}

function copyJsonPreview() {
  const json = document.getElementById("res-json-preview").textContent;
  navigator.clipboard.writeText(json);
  alert("Sample JSON copied to clipboard!");
}

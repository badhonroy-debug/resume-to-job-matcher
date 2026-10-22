/* Resume Matcher — frontend logic */

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initForms();
    initFileDrops();
    checkHealth();
});

/* ── Tabs ── */

function initTabs() {
    document.querySelectorAll(".tab").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(s => s.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
        });
    });
}

/* ── Health check ── */

async function checkHealth() {
    try {
        const res = await fetch("/api/health");
        const data = await res.json();
        if (!data.api_key_configured) {
            document.getElementById("api-warning").style.display = "block";
        }
    } catch { /* ignore */ }
}

/* ── File drop zones ── */

function initFileDrops() {
    document.querySelectorAll(".file-drop").forEach(drop => {
        const input = drop.querySelector("input[type=file]");
        const label = drop.querySelector(".file-drop-label");
        const defaultText = label.textContent;

        input.addEventListener("change", () => {
            if (input.files.length > 0) {
                const names = Array.from(input.files).map(f => f.name);
                label.textContent = names.join(", ");
                drop.classList.add("has-file");
            } else {
                label.textContent = defaultText;
                drop.classList.remove("has-file");
            }
        });

        // Drag-over highlight
        drop.addEventListener("dragover", (e) => {
            e.preventDefault();
            drop.classList.add("drag-over");
        });
        drop.addEventListener("dragleave", () => {
            drop.classList.remove("drag-over");
        });
        drop.addEventListener("drop", () => {
            drop.classList.remove("drag-over");
        });
    });
}

/* ── Forms ── */

function initForms() {
    setupForm("form-extract-resume", "/api/extract-resume", "result-extract-resume", renderResumeResult, "Analyzing resume with AI...");
    setupForm("form-extract-job", "/api/extract-job", "result-extract-job", renderJobResult, "Analyzing job description with AI...");
    setupForm("form-match", "/api/match", "result-match", renderMatchResult, "Extracting, scoring, and generating explanation... This involves multiple AI calls.");
    setupForm("form-rank", "/api/rank", "result-rank", renderRankResults, "Processing multiple resumes... This involves several AI calls per resume.");
}

function setupForm(formId, endpoint, resultId, renderFn, loadingMsg) {
    const form = document.getElementById(formId);
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const resultArea = document.getElementById(resultId);
        const btn = form.querySelector("button[type=submit]");

        resultArea.innerHTML = loadingHTML(loadingMsg);
        btn.disabled = true;

        try {
            const formData = new FormData(form);
            const res = await fetch(endpoint, { method: "POST", body: formData });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || "Request failed");
            }
            const data = await res.json();
            resultArea.innerHTML = renderFn(data);
            initExpandRows();
        } catch (err) {
            resultArea.innerHTML = `<div class="error-box">${escapeHtml(err.message)}</div>`;
        } finally {
            btn.disabled = false;
        }
    });
}

function loadingHTML(msg) {
    return `<div class="loading"><div class="spinner"></div><div class="loading-text">${escapeHtml(msg)}</div></div>`;
}

/* ── Renderers ── */

function renderResumeResult(data) {
    let html = `<div class="card">`;
    html += `<div class="data-section"><h4>Contact</h4><div class="data-grid">`;
    html += `<dt>Name</dt><dd>${esc(data.full_name)}</dd>`;
    if (data.email) html += `<dt>Email</dt><dd>${esc(data.email)}</dd>`;
    if (data.phone) html += `<dt>Phone</dt><dd>${esc(data.phone)}</dd>`;
    html += `<dt>Experience</dt><dd>${data.total_years_experience} years</dd>`;
    html += `</div></div>`;

    if (data.summary) {
        html += `<div class="data-section"><h4>Summary</h4><p style="font-size:0.9rem;color:var(--text-secondary)">${esc(data.summary)}</p></div>`;
    }

    if (data.skills.length) {
        html += `<div class="data-section"><h4>Skills</h4><div class="skill-pills">`;
        data.skills.forEach(s => {
            html += `<span class="pill matched" title="${esc(s.category)}">${esc(s.name)}</span>`;
        });
        html += `</div></div>`;
    }

    if (data.experience.length) {
        html += `<div class="data-section"><h4>Experience</h4>`;
        data.experience.forEach(exp => {
            html += `<div class="experience-item">`;
            html += `<div class="exp-title">${esc(exp.job_title)}</div>`;
            html += `<div class="exp-company">${esc(exp.company)} &middot; ${esc(exp.dates)}</div>`;
            if (exp.highlights.length) {
                html += `<ul class="exp-highlights">`;
                exp.highlights.forEach(h => { html += `<li>${esc(h)}</li>`; });
                html += `</ul>`;
            }
            html += `</div>`;
        });
        html += `</div>`;
    }

    if (data.education.length) {
        html += `<div class="data-section"><h4>Education</h4>`;
        data.education.forEach(edu => {
            html += `<div class="education-item">${esc(edu.degree)} in ${esc(edu.field)} &mdash; ${esc(edu.institution)}`;
            if (edu.graduation_year) html += ` (${edu.graduation_year})`;
            html += `</div>`;
        });
        html += `</div>`;
    }

    html += `</div>`;
    return html;
}

function renderJobResult(data) {
    let html = `<div class="card">`;
    html += `<div class="data-section"><h4>Position</h4><div class="data-grid">`;
    html += `<dt>Title</dt><dd>${esc(data.job_title)}</dd>`;
    if (data.company) html += `<dt>Company</dt><dd>${esc(data.company)}</dd>`;
    html += `<dt>Min Experience</dt><dd>${data.min_years_experience} years</dd>`;
    html += `<dt>Education</dt><dd>${esc(data.education_level)}</dd>`;
    html += `</div></div>`;

    if (data.required_skills.length) {
        html += `<div class="data-section"><h4>Required Skills</h4><div class="skill-pills">`;
        data.required_skills.forEach(s => {
            html += `<span class="pill missing" title="${esc(s.category)}">${esc(s.name)}</span>`;
        });
        html += `</div></div>`;
    }

    if (data.preferred_skills.length) {
        html += `<div class="data-section"><h4>Preferred Skills</h4><div class="skill-pills">`;
        data.preferred_skills.forEach(s => {
            html += `<span class="pill matched" title="${esc(s.category)}">${esc(s.name)}</span>`;
        });
        html += `</div></div>`;
    }

    if (data.responsibilities.length) {
        html += `<div class="data-section"><h4>Responsibilities</h4><ul style="padding-left:1.2rem;font-size:0.9rem;color:var(--text-secondary)">`;
        data.responsibilities.forEach(r => { html += `<li>${esc(r)}</li>`; });
        html += `</ul></div>`;
    }

    html += `</div>`;
    return html;
}

function renderMatchResult(data) {
    const color = scoreColor(data.overall_score);
    let html = `<div class="card">`;

    // Header: gauge + info
    html += `<div class="match-header">`;
    html += `<div class="score-gauge ${color}">${Math.round(data.overall_score)}</div>`;
    html += `<div class="match-info"><h3>${esc(data.candidate_name)}</h3>`;
    html += `<div class="job-title">${esc(data.job_title)}</div>`;
    html += `<div style="margin-top:0.35rem"><span class="badge ${data.recommendation}">${esc(data.recommendation.replace(/_/g, " "))}</span></div>`;
    html += `</div></div>`;

    // Breakdown
    html += `<div style="margin-top:1rem">`;
    html += breakdownBar("Required Skills", data.breakdown.required_skills_score);
    html += breakdownBar("Preferred Skills", data.breakdown.preferred_skills_score);
    html += breakdownBar("Experience", data.breakdown.experience_score);
    html += breakdownBar("Education", data.breakdown.education_score);
    html += `</div>`;

    // Skills
    html += `<div class="skills-section" style="margin-top:1rem">`;
    if (data.matched_skills.length) {
        html += `<div class="skills-col"><h4>Matched Skills</h4><div class="skill-pills">`;
        data.matched_skills.forEach(s => { html += `<span class="pill matched">${esc(s)}</span>`; });
        html += `</div></div>`;
    }
    if (data.missing_skills.length) {
        html += `<div class="skills-col"><h4>Missing Skills</h4><div class="skill-pills">`;
        data.missing_skills.forEach(s => { html += `<span class="pill missing">${esc(s)}</span>`; });
        html += `</div></div>`;
    }
    html += `</div>`;

    // Explanation
    if (data.explanation) {
        html += `<div class="explanation">${esc(data.explanation)}</div>`;
    }

    html += `</div>`;
    return html;
}

function renderRankResults(data) {
    if (!Array.isArray(data) || data.length === 0) {
        return `<div class="error-box">No results returned.</div>`;
    }

    let html = `<div class="card" style="padding:0;overflow:auto">`;
    html += `<table class="leaderboard">`;
    html += `<thead><tr><th>#</th><th>Candidate</th><th>Score</th><th>Recommendation</th><th></th></tr></thead>`;
    html += `<tbody>`;

    data.forEach((r, i) => {
        const color = scoreColor(r.overall_score);
        html += `<tr class="expandable" data-idx="${i}">`;
        html += `<td class="rank-num">${i + 1}</td>`;
        html += `<td>${esc(r.candidate_name)}</td>`;
        html += `<td><strong style="color:var(--${color})">${Math.round(r.overall_score)}</strong></td>`;
        html += `<td><span class="badge ${r.recommendation}">${esc(r.recommendation.replace(/_/g, " "))}</span></td>`;
        html += `<td style="color:var(--text-secondary);font-size:0.8rem">details</td>`;
        html += `</tr>`;

        // Expandable detail row
        html += `<tr class="expand-detail" id="detail-${i}"><td colspan="5">`;
        html += renderMatchResult(r);
        html += `</td></tr>`;
    });

    html += `</tbody></table></div>`;
    return html;
}

function initExpandRows() {
    document.querySelectorAll("tr.expandable").forEach(row => {
        row.addEventListener("click", () => {
            const detail = document.getElementById("detail-" + row.dataset.idx);
            if (detail) detail.classList.toggle("open");
        });
    });
}

/* ── Helpers ── */

function breakdownBar(label, score) {
    const color = scoreColor(score);
    return `<div class="breakdown-row">
        <span class="breakdown-label">${escapeHtml(label)}</span>
        <div class="breakdown-bar"><div class="breakdown-fill ${color}" style="width:${score}%"></div></div>
        <span class="breakdown-value">${Math.round(score)}</span>
    </div>`;
}

function scoreColor(score) {
    if (score >= 70) return "green";
    if (score >= 50) return "yellow";
    return "red";
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = String(text);
    return div.innerHTML;
}

const esc = escapeHtml;

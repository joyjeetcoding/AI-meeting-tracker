"""
Gradio UI — AI Meeting Action Tracker
---------------------------------------
Three tabs:
  1. Upload   — file or paste text → kicks off pipeline
  2. Results  — poll status, view summary + action items
  3. Meetings — table of all meetings

Talks to FastAPI at BACKEND_URL.
"""

import os
import httpx
import gradio as gr
from datetime import timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Priority styling ──────────────────────────────────────────
PRIORITY_EMOJI = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
STATUS_EMOJI   = {"pending": "⏳", "processing": "🔄", "done": "✅", "error": "❌"}


# ── API helpers ───────────────────────────────────────────────

def upload_meeting(title: str, file, text_input: str):
    if not title.strip():
        return "❌ Please enter a meeting title.", None
    if file is None and not (text_input or "").strip():
        return "❌ Please upload a file or paste meeting notes.", None

    try:
        if file is not None:
            with open(file.name, "rb") as f:
                r = httpx.post(
                    f"{BACKEND_URL}/upload-meeting/",
                    data={"title": title},
                    files={"file": (os.path.basename(file.name), f)},
                    timeout=30,
                )
        else:
            r = httpx.post(
                f"{BACKEND_URL}/upload-meeting/",
                data={"title": title, "text_input": text_input},
                timeout=30,
            )

        r.raise_for_status()
        meeting = r.json()
        mid = meeting["id"]
        return (
            f"✅ Meeting uploaded successfully!\n\n"
            f"**Meeting ID: `{mid}`**\n\n"
            f"Go to the **Results** tab and enter ID `{mid}` to track progress.",
            str(mid),
        )
    except httpx.HTTPError as e:
        return f"❌ Upload failed: {e}", None


def check_status(meeting_id: str):
    if not meeting_id.strip():
        return "Enter a meeting ID above and click Check Status."
    try:
        r = httpx.get(f"{BACKEND_URL}/meetings/{meeting_id}/status", timeout=10)
        r.raise_for_status()
        data   = r.json()
        status = data["status"]
        icon   = STATUS_EMOJI.get(status, "?")
        msgs   = {
            "pending":    "Pipeline is queued, starting soon...",
            "processing": "Agents are running — transcribing, summarizing, extracting...",
            "done":       "Pipeline complete! Click **Load Results** to view.",
            "error":      "Something went wrong. Check your server logs.",
        }
        return f"{icon} **{status.capitalize()}** — {msgs.get(status, '')}"
    except Exception as e:
        return f"❌ Error: {e}"


def load_results(meeting_id: str):
    if not meeting_id.strip():
        return "Enter a meeting ID above.", ""
    try:
        r = httpx.get(f"{BACKEND_URL}/get-summary/{meeting_id}", timeout=15)
        r.raise_for_status()
        data   = r.json()
        print("RAW API RESPONSE:", data)
        status = data.get("status", "unknown")

        if status != "done":
            icon = STATUS_EMOJI.get(status, "?")
            return f"{icon} Pipeline is **{status}**. Check status and try again shortly.", ""

        # ── Summary ───────────────────────────────────────────
        summary = data.get("summary") or "_No summary generated yet._"
        summary_md = f"### 📝 Summary\n\n{summary}"

        # ── Action items table ────────────────────────────────
        items = data.get("action_items", [])
        print("ITEMS:", items)
        print("ITEMS COUNT:", len(items))
        if not items:
            actions_md = "### ✅ Action Items\n\n_No action items found in this meeting._"
        else:
            lines = [
                "### ✅ Action Items\n",
                "| # | Task | Owner | Priority | Deadline | Status |",
                "|---|------|-------|----------|----------|--------|",
            ]
            print("First item keys:", items[0] if items else "empty")
            for item in items:
                icon     = PRIORITY_EMOJI.get(item.get("priority", "Medium"), "⚪")
                priority = f"{icon} {item.get('priority', 'Medium')}"
                owner    = item.get("owner") or "—"
                deadline = item.get("deadline") or "—"
                status   = item.get("status", "open")
                task     = item.get("task", "")
                db_id = item["id"]
                lines.append(f"| **{db_id}** | {task} | {owner} | {priority} | {deadline} | {status} |")
            actions_md = "\n".join(lines)

        return summary_md, actions_md

    except Exception as e:
        return f"❌ Error loading results: {e}", ""


def load_all_meetings():
    try:
        r = httpx.get(f"{BACKEND_URL}/meetings", timeout=10)
        r.raise_for_status()
        meetings = r.json()

        if not meetings:
            return (
                "### 📁 All Meetings\n\n"
                "_No meetings yet. Upload one in the **Upload** tab to get started._"
            )

        lines = [
            "### 📁 All Meetings\n",
            "| ID | Title | Status | Actions | Uploaded |",
            "|----|-------|--------|---------|----------|",
        ]
        for m in meetings:
            icon    = STATUS_EMOJI.get(m.get("status", ""), "?")
            status  = f"{icon} {m.get('status', '').capitalize()}"
            from datetime import datetime
            raw = m.get("created_at", "")
            try:
                dt = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc).astimezone(IST)
                created = dt.strftime("%d %b %Y %I:%M %p")
            except:
                created = str(raw)[:16].replace("T", " ")
            lines.append(
                f"| {m['id']} | {m.get('title', '')} | {status} "
                f"| {m.get('action_count', 0)} | {created} |"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


def update_action(action_id: str, new_status: str, owner: str, priority: str, deadline: str):
    if not action_id.strip():
        return "❌ Enter an action item ID."
    try:
        # Only send fields that are actually filled in
        payload = {"status": new_status, "priority": priority}
        if owner.strip():
            payload["owner"] = owner.strip()
        if deadline.strip():
            payload["deadline"] = deadline.strip()

        r = httpx.patch(
            f"{BACKEND_URL}/update-action/{action_id}",
            json=payload,
            timeout=10,
        )
        r.raise_for_status()
        item = r.json()
        return (
            f"✅ Action item **#{action_id}** updated\n\n"
            f"**Task:** {item.get('task', '')}\n\n"
            f"**Owner:** {item.get('owner') or '—'} | "
            f"**Priority:** {item.get('priority')} | "
            f"**Deadline:** {item.get('deadline') or '—'} | "
            f"**Status:** {item.get('status')}"
        )
    except Exception as e:
        return f"❌ Error: {e}"

# ── Custom CSS ────────────────────────────────────────────────
CSS = """
/* ── Base ────────────────────────────────────────── */
.gradio-container {
    max-width: 860px !important;
    margin: 0 auto !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Header ──────────────────────────────────────── */
.app-header {
    text-align: center;
    padding: 2rem 1rem 1rem;
    border-bottom: 1px solid var(--border-color-primary);
    margin-bottom: 1.5rem;
}
.app-header h1 {
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0 0 0.4rem;
    color: var(--body-text-color);
    letter-spacing: -0.5px;
}
.app-header p {
    font-size: 0.95rem;
    color: var(--body-text-color-subdued);
    margin: 0;
}

/* ── Buttons ──────────────────────────────────────── */
.primary-btn {
    background: #2563eb !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 0.6rem 1.2rem !important;
    transition: background 0.2s !important;
}
.primary-btn:hover {
    background: #1d4ed8 !important;
}
.secondary-btn {
    background: #059669 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: background 0.2s !important;
}
.secondary-btn:hover {
    background: #047857 !important;
}

/* ── Cards ────────────────────────────────────────── */
.info-card {
    background: var(--background-fill-secondary);
    border: 1px solid var(--border-color-primary);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
    font-size: 0.9rem;
    line-height: 1.6;
    color: var(--body-text-color-subdued);
}

/* ── Status box ───────────────────────────────────── */
.status-box {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.9rem !important;
    border-radius: 8px !important;
}

/* ── Tables ───────────────────────────────────────── */
.gr-markdown table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
    margin-top: 0.5rem;
}
.gr-markdown th {
    background: var(--background-fill-secondary);
    padding: 0.5rem 0.75rem;
    text-align: left;
    font-weight: 600;
    border-bottom: 2px solid var(--border-color-primary);
}
.gr-markdown td {
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--border-color-primary);
    vertical-align: top;
}

/* ── Mobile responsive ────────────────────────────── */
@media (max-width: 640px) {
    .gradio-container {
        padding: 0 0.5rem !important;
    }
    .app-header h1 {
        font-size: 1.4rem !important;
    }
    .gr-markdown table {
        font-size: 0.78rem !important;
    }
    .gr-markdown th,
    .gr-markdown td {
        padding: 0.35rem 0.5rem !important;
    }
}
"""


# ── Gradio Layout ─────────────────────────────────────────────

with gr.Blocks(
    title="AI Meeting Action Tracker",
    theme=gr.themes.Soft(
        primary_hue=gr.themes.colors.blue,
        neutral_hue=gr.themes.colors.slate,
        font=gr.themes.GoogleFont("Inter"),
    ),
    css=CSS,
) as demo:

    # ── Header ────────────────────────────────────────────────
    gr.HTML("""
    <div class="app-header">
        <h1>AI Meeting Action Tracker</h1>
        <p>Upload meeting audio or notes → AI extracts decisions and action items automatically</p>
    </div>
    """)

    with gr.Tabs():

        # ── Tab 1: Upload ──────────────────────────────────────
        with gr.Tab("📤 Upload Meeting"):

            gr.HTML("""
            <div class="info-card">
                Upload an audio recording (.mp3, .wav, .m4a, .mp4) or paste your meeting notes below.
                The AI will transcribe, summarize, and extract action items automatically.
            </div>
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    title_input = gr.Textbox(
                        label="Meeting Title",
                        placeholder="e.g. Q3 Sprint Planning — June 10",
                        max_lines=1,
                    )
                    file_input = gr.File(
                        label="Audio or Text File (optional)",
                        file_types=[".mp3", ".wav", ".m4a", ".ogg", ".txt", ".md", ".mp4"],
                    )
                    text_input = gr.Textbox(
                        label="Or paste meeting notes here",
                        placeholder="Joy will finish the auth module by Friday.\nSam will send the proposal to the client by Thursday...",
                        lines=10,
                        max_lines=20,
                    )
                    upload_btn = gr.Button(
                        "🚀 Process Meeting",
                        elem_classes=["primary-btn"],
                        variant="primary",
                    )

                with gr.Column(scale=1):
                    upload_status = gr.Markdown(
                        value="Upload a meeting to get started.",
                        label="Status",
                    )
                    last_id = gr.State(value="")

            upload_btn.click(
                fn=upload_meeting,
                inputs=[title_input, file_input, text_input],
                outputs=[upload_status, last_id],
            )

        # ── Tab 2: Results ─────────────────────────────────────
        with gr.Tab("📋 Results"):

            gr.HTML("""
            <div class="info-card">
                Enter your meeting ID to check pipeline progress and view results.
                Use <b>Check Status</b> to poll progress, then <b>Load Results</b> when done.
            </div>
            """)

            with gr.Row():
                result_id   = gr.Textbox(
                    label="Meeting ID",
                    placeholder="e.g. 1",
                    scale=3,
                    max_lines=1,
                )
                status_btn  = gr.Button("🔄 Check Status", scale=1)
                load_btn    = gr.Button(
                    "📥 Load Results",
                    scale=1,
                    elem_classes=["secondary-btn"],
                    variant="secondary",
                )

            status_out  = gr.Markdown(
                value="Enter a meeting ID and check status.",
                elem_classes=["status-box"],
            )
            summary_out = gr.Markdown()
            actions_out = gr.Markdown()

            status_btn.click(fn=check_status, inputs=result_id, outputs=status_out)
            load_btn.click(fn=load_results,   inputs=result_id, outputs=[summary_out, actions_out])

            gr.Markdown("---")
            gr.Markdown("### ✏️ Update Task")

            gr.HTML("""
            <div class="info-card">
                Enter the action item ID from the table above and update any field you want.
                Leave fields blank to keep them unchanged.
            </div>
            """)

            with gr.Row():
                action_id_input = gr.Textbox(
                    label="Action Item ID",
                    placeholder="e.g. 11",
                    scale=1,
                    max_lines=1,
                )
                status_dropdown = gr.Dropdown(
                    choices=["open", "in_progress", "done"],
                    value="open",
                    label="Status",
                    scale=1,
                )

            with gr.Row():
                owner_input = gr.Textbox(
                    label="Owner (leave blank to keep unchanged)",
                    placeholder="e.g. Joy",
                    scale=1,
                    max_lines=1,
                )
                priority_dropdown = gr.Dropdown(
                    choices=["High", "Medium", "Low"],
                    value="Medium",
                    label="Priority",
                    scale=1,
                )
                deadline_input = gr.Textbox(
                    label="Deadline (leave blank to keep unchanged)",
                    placeholder="e.g. Friday",
                    scale=1,
                    max_lines=1,
                )

            update_btn = gr.Button("Update Task", elem_classes=["secondary-btn"])
            update_out = gr.Markdown()

            update_btn.click(
                fn=update_action,
                inputs=[action_id_input, status_dropdown, owner_input, priority_dropdown, deadline_input],
                outputs=update_out,
            )

        # ── Tab 3: All Meetings ────────────────────────────────
        with gr.Tab("📁 All Meetings"):

            gr.HTML("""
            <div class="info-card">
                All uploaded meetings and their current pipeline status.
            </div>
            """)

            refresh_btn      = gr.Button("🔄 Refresh", elem_classes=["secondary-btn"])
            all_meetings_out = gr.Markdown()

            refresh_btn.click(fn=load_all_meetings, outputs=all_meetings_out)
            demo.load(fn=load_all_meetings,         outputs=all_meetings_out)

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_api=False,
        favicon_path=None,
    )
"""
Persona Hub — HPEP-100 Agent Library
Hugging Face Spaces deployment with Gradio + Claude API + MCP server
"""
import os
import gradio as gr
from anthropic import Anthropic
from personas import PERSONAS, CATEGORIES, get_persona_choices, name_from_choice, build_hpep_bar

_TOTAL_PERSONAS = len(PERSONAS)

# ── Client ────────────────────────────────────────────────────────────────────
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

# ── Chat function ─────────────────────────────────────────────────────────────
def chat(message: str, history: list, persona_choice: str, temperature: float):
    pid = name_from_choice(persona_choice)
    persona = PERSONAS[pid]
    system = persona["system_prompt"]

    messages = []
    for h in history:
        if h["role"] in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        temperature=temperature,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def respond(message, history, persona_choice, temperature):
    if not message.strip():
        return history, history
    reply = chat(message, history, persona_choice, temperature)
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]
    return history, history


def switch_persona(persona_choice, history):
    pid = name_from_choice(persona_choice)
    p = PERSONAS[pid]
    hpep_md = build_hpep_bar(p["hpep"])
    profile = f"""### {p['emoji']} {p['name']}
**Era:** {p['era']}
**Domain:** {p['domain']}
**CEID:** {p['ceid']:.3f}

> *"{p['tagline']}"*

**HPEP-100 Profile:**
{hpep_md}

**Tags:** {' · '.join(f'`{t}`' for t in p['tags'])}
"""
    intro_msg = f"*[Persona activated: {p['name']}]*"
    new_history = history + [{"role": "assistant", "content": intro_msg}]
    return profile, new_history, new_history


def clear_chat():
    return [], []


# ── Gradio Tools (MCP-exposed) ────────────────────────────────────────────────
def list_personas(category: str = "All") -> str:
    """List available personas, optionally filtered by category."""
    ids = CATEGORIES.get(category, CATEGORIES["All"])
    lines = [f"## Personas ({category})\n"]
    for pid in ids:
        p = PERSONAS[pid]
        lines.append(f"- **{p['emoji']} {p['name']}** ({p['era']}) — CEID {p['ceid']:.3f}")
        lines.append(f"  > {p['tagline']}")
    return "\n".join(lines)


def get_persona_profile(persona_name: str) -> str:
    """Get the full HPEP-100 profile for a persona by name."""
    pid = None
    for k, p in PERSONAS.items():
        if persona_name.lower() in p["name"].lower() or persona_name.lower() == k:
            pid = k
            break
    if not pid:
        return f"Persona '{persona_name}' not found. Available: {', '.join(p['name'] for p in PERSONAS.values())}"
    p = PERSONAS[pid]
    return f"# {p['emoji']} {p['name']}\n\n{p['tagline']}\n\n**HPEP:**\n{build_hpep_bar(p['hpep'])}\n\nCEID: {p['ceid']:.3f}"


def compare_personas(name_a: str, name_b: str) -> str:
    """Compare two personas by their HPEP-100 block values."""
    def find(name):
        for k, p in PERSONAS.items():
            if name.lower() in p["name"].lower() or name.lower() == k:
                return k, p
        return None, None

    kid_a, pa = find(name_a)
    kid_b, pb = find(name_b)
    if not pa or not pb:
        return "One or both personas not found."

    lines = [f"## {pa['emoji']} {pa['name']} vs {pb['emoji']} {pb['name']}\n"]
    lines.append(f"| Block | {pa['name'][:12]} | {pb['name'][:12]} | Δ |")
    lines.append("|-------|---------|---------|---|")
    for block in pa["hpep"]:
        va, vb = pa["hpep"][block], pb["hpep"][block]
        delta = va - vb
        sign = "+" if delta > 0 else ""
        lines.append(f"| {block:<12} | {va:.2f} | {vb:.2f} | {sign}{delta:.2f} |")
    lines.append(f"\n**CEID:** {pa['name']} {pa['ceid']:.3f} vs {pb['name']} {pb['ceid']:.3f}")
    return "\n".join(lines)


# ── UI ────────────────────────────────────────────────────────────────────────
with gr.Blocks(
    title="Persona Hub — HPEP-100 Agents",
    theme=gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="purple",
        neutral_hue="slate",
    ),
    css="""
    .persona-profile { font-family: monospace; font-size: 0.85em; }
    .title-block { text-align: center; padding: 1em 0; }
    """,
) as demo:

    # ── Header ────────────────────────────────────────────────────────────────
    gr.HTML(f"""
    <div class="title-block">
        <h1>🎭 Persona Hub</h1>
        <p>{_TOTAL_PERSONAS} mathematically profiled cognitive agents — powered by HPEP-100</p>
    </div>
    """)

    with gr.Row():
        # ── Left panel — Persona selector ─────────────────────────────────────
        with gr.Column(scale=1, min_width=280):
            gr.Markdown(f"### Select Persona ({_TOTAL_PERSONAS} available)")

            category_filter = gr.Dropdown(
                choices=list(CATEGORIES.keys()),
                value="All",
                label="Category",
                interactive=True,
            )

            search_box = gr.Textbox(
                placeholder="Search by name, era, or domain...",
                label="Search",
                show_label=True,
            )

            persona_selector = gr.Dropdown(
                choices=get_persona_choices(),
                value=get_persona_choices()[0],
                label="Persona",
                interactive=True,
            )

            temperature = gr.Slider(
                minimum=0.0, maximum=1.0, value=0.7, step=0.05,
                label="Temperature",
                info="Higher = more creative, lower = more focused",
            )

            activate_btn = gr.Button("⚡ Activate Persona", variant="primary")
            clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")

            gr.Markdown("---")
            persona_profile = gr.Markdown(
                value="*Select a persona and click Activate.*",
                elem_classes=["persona-profile"],
            )

        # ── Right panel — Chat ────────────────────────────────────────────────
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                type="messages",
                height=520,
                show_copy_button=True,
                avatar_images=(None, "https://api.dicebear.com/7.x/bottts/svg?seed=persona"),
                label="Conversation",
            )
            state = gr.State([])

            with gr.Row():
                msg_box = gr.Textbox(
                    placeholder="Type your message...",
                    show_label=False,
                    scale=5,
                    container=False,
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)

    # ── Tools tab (MCP) ───────────────────────────────────────────────────────
    with gr.Accordion("🔧 API Tools (MCP-exposed)", open=False):
        gr.Markdown("These functions are exposed as MCP tools when the Space is used as an MCP server.")

        with gr.Row():
            with gr.Column():
                gr.Markdown("**List Personas**")
                cat_input = gr.Dropdown(
                    choices=list(CATEGORIES.keys()), value="All", label="Category"
                )
                list_btn = gr.Button("List")
                list_output = gr.Markdown()
                list_btn.click(list_personas, inputs=cat_input, outputs=list_output)

            with gr.Column():
                gr.Markdown("**Compare Two Personas**")
                compare_a = gr.Textbox(label="Persona A", placeholder="e.g. socrates")
                compare_b = gr.Textbox(label="Persona B", placeholder="e.g. machiavelli")
                compare_btn = gr.Button("Compare")
                compare_output = gr.Markdown()
                compare_btn.click(compare_personas, inputs=[compare_a, compare_b], outputs=compare_output)

    # ── Event wiring ──────────────────────────────────────────────────────────
    activate_btn.click(
        fn=switch_persona,
        inputs=[persona_selector, state],
        outputs=[persona_profile, chatbot, state],
    )

    def _filter_choices(cat: str, query: str) -> gr.Dropdown:
        ids = CATEGORIES.get(cat, CATEGORIES["All"])
        q = query.strip().lower()
        if q:
            ids = [
                pid for pid in ids
                if q in PERSONAS[pid]["name"].lower()
                or q in PERSONAS[pid].get("era", "").lower()
                or q in PERSONAS[pid].get("domain", "").lower()
                or any(q in t.lower() for t in PERSONAS[pid].get("tags", []))
            ]
        choices = [
            f"{PERSONAS[pid]['emoji']} {PERSONAS[pid]['name']} — {PERSONAS[pid]['era']}"
            for pid in ids
        ]
        return gr.Dropdown(choices=choices, value=choices[0] if choices else None)

    category_filter.change(
        fn=_filter_choices,
        inputs=[category_filter, search_box],
        outputs=persona_selector,
    )

    search_box.change(
        fn=_filter_choices,
        inputs=[category_filter, search_box],
        outputs=persona_selector,
    )

    send_btn.click(
        fn=respond,
        inputs=[msg_box, state, persona_selector, temperature],
        outputs=[chatbot, state],
    ).then(lambda: "", outputs=msg_box)

    msg_box.submit(
        fn=respond,
        inputs=[msg_box, state, persona_selector, temperature],
        outputs=[chatbot, state],
    ).then(lambda: "", outputs=msg_box)

    clear_btn.click(fn=clear_chat, outputs=[chatbot, state])

    gr.HTML("""
    <div style="text-align:center; padding: 1.5em 1em 1em; border-top: 1px solid #e5e7eb; margin-top: 1em;">
        <p style="color:#4f46e5; font-size:1em; margin-bottom:0.5em;">
            <strong>Want voice synthesis, all 495+ personas &amp; API access?</strong>
        </p>
        <a href="https://github.com/mk350174-cmd/Persona" target="_blank"
           style="display:inline-block; background:#4f46e5; color:white; padding:0.5em 1.4em;
                  border-radius:8px; text-decoration:none; font-weight:600; margin:0 0.3em;">
           🚀 Get Full API
        </a>
        <a href="https://github.com/mk350174-cmd/Persona#readme" target="_blank"
           style="display:inline-block; background:#f1f5f9; color:#334155; padding:0.5em 1.4em;
                  border-radius:8px; text-decoration:none; font-weight:600; margin:0 0.3em;">
           📖 Docs
        </a>
        <p style="color:#94a3b8; font-size:0.75em; margin-top:0.7em;">
            HPEP-100 Persona Mathematics | CEID v2.0
        </p>
    </div>
    """)

# ── Launch (with MCP server) ──────────────────────────────────────────────────
if __name__ == "__main__":
    demo.launch(mcp_server=True)

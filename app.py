"""Simple Gradio application for the MSAI 631 development environment exercise."""

import gradio as gr


def create_greeting(name: str) -> str:
    """Return a friendly message that confirms the environment is working."""
    clean_name = name.strip() or "Class"
    return (
        f"Hello, {clean_name}! "
        "The MSAI 631 GitHub-linked development environment is working."
    )


demo = gr.Interface(
    fn=create_greeting,
    inputs=gr.Textbox(label="Your name", placeholder="Enter a name"),
    outputs=gr.Textbox(label="Greeting"),
    title="MSAI 631 Hello HCI",
    description=(
        "A simple Gradio application created to verify the course "
        "development environment."
    ),
    examples=[["Yasharth"], ["Professor Dennis"]],
)


if __name__ == "__main__":
    # Bind to all interfaces so GitHub Codespaces can forward port 7860.
    demo.launch(server_name="0.0.0.0", server_port=7860)

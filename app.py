"""Local Gradio application for the MSAI 631 environment exercise."""

import os

import gradio as gr


def create_greeting(name: str) -> str:
    """Return a greeting that confirms the local application is working."""
    clean_name = name.strip() or "Class"
    return (
        f"Hello, {clean_name}! "
        "The MSAI 631 local Python and Gradio environment is working."
    )


demo = gr.Interface(
    fn=create_greeting,
    inputs=gr.Textbox(label="Your name", placeholder="Enter a name"),
    outputs=gr.Textbox(label="Greeting"),
    title="MSAI 631 Local Development Environment",
    description=(
        "A simple human-computer interaction created to verify the local "
        "development environment before synchronizing the project with GitHub."
    ),
    examples=[["Yasharth"], ["Professor Dennis"]],
)


if __name__ == "__main__":
    server_name = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    demo.launch(server_name=server_name, server_port=server_port)

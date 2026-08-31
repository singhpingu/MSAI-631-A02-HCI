# MSAI-631-A02-HCI

This private repository supports coursework for **MSAI-631-A02: Artificial Intelligence for Human-Computer Interaction** at the University of the Cumberlands.

The Week 1 project demonstrates a local development environment created on a MacBook with Visual Studio Code, Python 3.12.10, a Python virtual environment, Git, GitHub, and Gradio. The application was developed and tested locally before the completed files were committed and pushed to GitHub.

## Project files

```text
MSAI-631-A02-HCI/
├── .devcontainer/
│   └── devcontainer.json
├── .vscode/
│   ├── extensions.json
│   └── settings.json
├── .gitignore
├── .python-version
├── README.md
├── app.py
└── requirements.txt
```

The `.devcontainer` configuration is optional. It provides a reproducible Python 3.12 environment, but it was not the primary environment used for the assignment.

## Prerequisites for macOS

Install the following software before beginning:

- Git
- Visual Studio Code
- The Python and Pylance extensions for Visual Studio Code
- Python 3.12.10

Confirm Git and Python from Terminal:

```bash
git --version
python3.12 --version
```

If the `code` command is unavailable, open Visual Studio Code, press **Shift + Command + P**, and select **Shell Command: Install 'code' command in PATH**. Restart Terminal afterward.

## Clone the private repository

The GitHub account used to clone this private repository must have permission to access it. GitHub does not accept an account password for Git operations over HTTPS. Use GitHub's browser authentication, GitHub CLI, a personal access token, or an existing SSH key.

### Recommended method: GitHub CLI

Authenticate securely in a browser:

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
gh auth status
```

Then clone and open the project:

```bash
mkdir -p ~/Documents/GitHub
cd ~/Documents/GitHub
gh repo clone singhpingu/MSAI-631-A02-HCI
cd MSAI-631-A02-HCI
code .
```

### Alternative method: Git over HTTPS

```bash
mkdir -p ~/Documents/GitHub
cd ~/Documents/GitHub
git clone https://github.com/singhpingu/MSAI-631-A02-HCI.git
cd MSAI-631-A02-HCI
code .
```

If prompted, complete GitHub authentication in the browser or use a personal access token as the password. Never place a token in the clone URL, a project file, or a screenshot.

## Create the local Python environment

In the Visual Studio Code terminal, run:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
```

The Python version should display `Python 3.12.10`. In Visual Studio Code, press **Shift + Command + P**, select **Python: Select Interpreter**, and choose `.venv/bin/python`.

## Run and test the Gradio application

With `(.venv)` visible in the terminal prompt, run:

```bash
python app.py
```

Open the local address shown in the terminal, normally:

```text
http://0.0.0.1:7860
```

Enter a name and confirm that the application returns a greeting. Press **Control + C** in the terminal to stop the server. Run `deactivate` when the virtual environment is no longer needed.

## Verify the setup

```bash
python --version
python -c "from importlib.metadata import version; print('Gradio:', version('gradio')); print('SocksIO:', version('socksio'))"
git remote -v
git branch --show-current
git status
```

The remote should point to `https://github.com/singhpingu/MSAI-631-A02-HCI.git`, the branch should be `main`, and a fully synchronized repository should report a clean working tree.

## Update an existing local clone

If the repository was cloned previously, open its folder and retrieve the latest files:

```bash
cd ~/Documents/GitHub/MSAI-631-A02-HCI
git pull --ff-only origin main
source .venv/bin/activate
python -m pip install -r requirements.txt
code .
```

## Save and push later work

After testing changes locally:

```bash
git status
git add .
git commit -m "Describe the completed change"
git push origin main
```

Review `git status` before committing. The `.gitignore` file prevents the local virtual environment, Python cache files, macOS metadata, and secret environment files from being committed.

## Troubleshooting

- **`Repository not found`:** Confirm the repository URL and authenticate with a GitHub account that has access to the private repository.
- **`python3.12: command not found`:** Install Python 3.12.10, restart Terminal, and run the version command again.
- **Wrong Python interpreter in Visual Studio Code:** Select `.venv/bin/python` with the **Python: Select Interpreter** command.
- **`No module named gradio`:** Activate `.venv` and rerun `python -m pip install -r requirements.txt`.
- **Port 7860 is already in use:** Stop the earlier server with **Control + C**, or identify it with `lsof -nP -iTCP:7860 -sTCP:LISTEN`.
- **Existing destination folder:** Enter the existing repository and run `git pull --ff-only origin main` instead of cloning over it.

## Repository access

This course repository is private. The instructor account, `AlanAtUC`, should retain collaborator access with permission to read the repository.

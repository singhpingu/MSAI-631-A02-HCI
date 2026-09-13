# Traditional Chatbot: Course Development Helper

This project is a local, traditional chatbot prototype for MSAI 631 A02. It uses Python regular expressions and prepared replies. It has no LLM, trained model, external AI API, package dependency, telemetry, or cloud deployment. The user interface is plain HTML, CSS, and JavaScript served by Python's standard library.

Project repository: https://github.com/singhpingu/MSAI-631-A02-HCI

The project is supplied for **local testing first**. No GitHub change, invitation, or successful Windows run is implied by these files. Keep the repository private and verify instructor access for `AlanAtUC` before eventual submission.

## 1. Check Windows prerequisites

Open **PowerShell** from the Windows Start menu. Run:

```powershell
git --version
py -3.12 --version
```

Use Python 3.12 to match the course repository. If Python is missing, install a Python 3.12 Windows installer from the official Python website. Include the Python launcher during installation, and then open a new PowerShell window. VS Code's Python extension does not install Python. If `git` is missing, install Git for Windows from the official Git website and reopen PowerShell.

Official project sites: https://www.python.org/ and https://git-scm.com/ and https://code.visualstudio.com/

## 2. Clone the existing course repository

Run these commands in PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path 'C:\Users\ysingh\Desktop\UC' | Out-Null
Set-Location 'C:\Users\ysingh\Desktop\UC'
git clone https://github.com/singhpingu/MSAI-631-A02-HCI.git
Set-Location 'C:\Users\ysingh\Desktop\UC\MSAI-631-A02-HCI'
git remote -v
git status
```

If Git prompts for authentication, use Git Credential Manager's browser sign in with the GitHub account that owns or can access the private repository. Never paste a password or token into the URL or chatbot. A private repository can produce a “not found” error when the wrong account is signed in.

If `MSAI-631-A02-HCI` already exists, **do not delete it or clone over it**. Open it, run `git status` and `git remote -v`, and confirm the remote matches the course repository. Preserve any local work before fetching updates.

Open VS Code, choose **File > Open Folder**, and select:

```text
C:\Users\ysingh\Desktop\UC\MSAI-631-A02-HCI
```

## 3. Put the supplied chatbot files inside that clone

Extract the supplied project ZIP to a temporary folder with Windows File Explorer. The ZIP contains a folder named `traditional_chatbot`. Copy that folder into the course repository so the files are located here:

```text
C:\Users\ysingh\Desktop\UC\MSAI-631-A02-HCI\traditional_chatbot\app.py
C:\Users\ysingh\Desktop\UC\MSAI-631-A02-HCI\traditional_chatbot\engine.py
C:\Users\ysingh\Desktop\UC\MSAI-631-A02-HCI\traditional_chatbot\README.md
```

Do not create a second `traditional_chatbot` folder inside the first one. If a folder with that name already exists, compare or back it up before replacing files. This project is separate from the earlier Gradio assignment and should not replace that assignment's files.

## 4. Create and select the local Python environment

In VS Code, open **Terminal > New Terminal** and make sure the terminal is PowerShell. Run:

```powershell
Set-Location 'C:\Users\ysingh\Desktop\UC\MSAI-631-A02-HCI\traditional_chatbot'
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe --version
```

In VS Code, install Microsoft's Python extension if needed. Press **Ctrl+Shift+P**, choose **Python: Select Interpreter**, choose **Enter interpreter path** if necessary, and select:

```text
C:\Users\ysingh\Desktop\UC\MSAI-631-A02-HCI\traditional_chatbot\.venv\Scripts\python.exe
```

There are no third party packages to install. The `requirements.txt` file documents this intentionally. The commands call the virtual environment's interpreter directly, so you do not need to activate it or change PowerShell's execution policy.

## 5. Run the automated checks and capture your actual result

Run in the same terminal:

```powershell
New-Item -ItemType Directory -Force -Path '.\evidence' | Out-Null
.\.venv\Scripts\python.exe --version 2>&1 | Tee-Object -FilePath '.\evidence\windows_validation.txt'
.\.venv\Scripts\python.exe -c "import platform; print(platform.platform())" 2>&1 | Tee-Object -FilePath '.\evidence\windows_validation.txt' -Append
.\.venv\Scripts\python.exe -m unittest discover -s tests -v 2>&1 | Tee-Object -FilePath '.\evidence\windows_validation.txt' -Append
$chatbotTestExitCode = $LASTEXITCODE
"Test exit code: $chatbotTestExitCode" | Tee-Object -FilePath '.\evidence\windows_validation.txt' -Append
```

An exit code of `0` and a final `OK` indicate the automated suite passed. Keep any actual errors in your notes. `evidence/assistant_validation.txt` records checks in the assistant's environment only and is not evidence of a Windows run. Automated tests cover specific behavior; they do not prove every interaction works or replace manual usability testing.

## 6. Start the chatbot locally

```powershell
.\.venv\Scripts\python.exe app.py
```

Keep the terminal open. In Edge, Chrome, or Firefox, go to:

```text
http://127.0.0.1:3978
```

Type messages into the browser interface. To stop the application, click the terminal and press **Ctrl+C**. If port 3978 is already in use, start with `.\.venv\Scripts\python.exe app.py --port 3979` and open `http://127.0.0.1:3979` instead.

## 7. Try the manual interaction checklist

| Prompt or action | Expected behavior |
| --- | --- |
| `hello` | Greeting and a suggestion to ask for help. |
| `help` | Capabilities and limitations are listed. |
| `How do I clone the repository?` | Fixed clone instructions for the course repository. |
| `How do I create a Python virtual environment?` | Python 3.12 virtual environment commands. |
| `How do I run tests?` | The unittest command and limitations of testing. |
| `echo: Hello Yasharth` | The same text after the colon. |
| `reverse: hello` | `olleh`. |
| `Tell me about Python and repository privacy` | Clarification because two topics are present. |
| `What is the weather tomorrow?` | A useful fallback without an invented answer. |
| Send a blank message | No empty message is sent; an input prompt appears. |
| `echo: <script>alert(1)</script>` | The literal text is displayed, and nothing executes. |
| Tab through the interface | Controls can be reached with the keyboard. |
| Clear conversation | Visible conversation history is reset. |
| Stop the server and try another message | A readable connection error appears. Restart to continue. |

Each request is independent. Follow ups such as “What about that?” cannot refer to earlier messages. The visible conversation is a display history, not chatbot memory.

## 8. Capture real Windows screenshots for the later report

Use **Win+Shift+S**, choose a rectangular snip, and capture only the relevant area. Open the notification and save the image. Avoid account menus, tokens, personal files, and unrelated windows.

1. **Local project and interpreter:** VS Code Explorer showing `traditional_chatbot`, with the terminal displaying the Python version and the selected interpreter visible if convenient.
2. **Automated validation:** VS Code terminal showing the final test count, `OK` or the actual failure, and the exit code. Preserve the full text log separately.
3. **Normal interactions:** Browser showing `help`, a supported question, and the replies with the local URL visible.
4. **Fallback and clarification:** Browser showing an unsupported question and a question containing two topics, with the chatbot's actual responses.
5. **Source control when ready:** VS Code Source Control or `git status` showing the added project files. Capture GitHub after a real push only if you subsequently choose to publish the tested work there.

For the report, give each figure a number and a descriptive italicized title, and discuss the observation in a narrative paragraph. Do not describe planned actions as completed. Send the test log, screenshots, and actual difficulties back for the final 5 to 7 page APA report.

## 9. Development lifecycle reflected in this prototype

**Define:** Keep the task small: a course development FAQ helper with explicit capabilities and a helpful fallback.

**Design:** Separate the browser, HTTP transport, and response engine. Use named regex rules and a `ChatAdapter` protocol so the current rule engine could later be replaced deliberately.

**Implement:** Normalize text, validate input, match commands and FAQ rules, resolve common overlaps, and return a stable `ChatReply` record.

**Test:** Run engine and actual loopback HTTP tests. Then inspect keyboard navigation, feedback, clarification, and recovery in a browser.

**Refine:** Document vocabulary gaps, misleading matches, unclear replies, and observed failures. Change a specific rule or prompt and rerun relevant checks.

**Package and maintain:** Keep source under version control, preserve the actual validation evidence, and create a clean ZIP. Expand the domain only when it serves a defined user need.

## 10. Build the submission ZIP after local testing

```powershell
.\.venv\Scripts\python.exe make_archive.py
```

The archive is created at:

```text
C:\Users\ysingh\Desktop\UC\MSAI-631-A02-HCI\traditional_chatbot\dist\traditional_chatbot.zip
```

The script uses an explicit file allowlist. It includes source code, instructions, tests, and available validation logs. It excludes `.venv`, `.git`, credentials, unrelated assignments, and generated archives. It also writes a SHA-256 manifest. Review validation logs before sharing them. Add figures to the Word report separately; the ZIP is the code archive.

## Troubleshooting and known limits

| Observation | Resolution or honest limitation |
| --- | --- |
| `py -3.12` is not recognized or Python 3.12 is unavailable | Install Python 3.12 with its launcher and reopen PowerShell, or use the verified full path to that Python installation. |
| Private repository clone says “not found” | Confirm the repository URL and sign in with an account that has access. |
| `app.py` cannot be found | Check the current folder and remove accidental double nesting from ZIP extraction. |
| Browser cannot connect | Keep the server terminal running and use the exact URL and port printed there. |
| Port already in use | Stop your earlier instance with Ctrl+C or choose `--port 3979`. |
| A phrase is not recognized or gets the wrong answer | This is a limited keyword and regex system. Record the exact input, add an explicit rule if justified, and retest. |
| A question mentions several topics | The bot requests one topic at a time, except for expected overlaps such as cloning a repository or a Python virtual environment. |
| The rule gives generic instructions when a user expresses a different intent | Keyword rules do not understand meaning. Document this limitation; do not interpret a matched rule as comprehension. |
| Unicode reverse looks strange for some emoji | Reversal operates on Unicode code points, not full visual grapheme clusters. |

This is a classroom prototype. Python's basic HTTP server is not a production deployment server. It binds to `127.0.0.1` and serves only allowlisted files. The API rejects invalid JSON, unsupported shapes and text types, blank input, excessive input, and requests with an external Host or Origin. Chat text is not stored in files or sent to any external service by the application. The browser keeps visible history until cleared or refreshed. The terminal logs request addresses and status codes, not message bodies. Do not enter sensitive information.

## AI Tools and Project Repository Disclosure

OpenAI ChatGPT/Codex assisted with project planning, code generation, documentation, and automated validation in a separate execution environment. The implemented chatbot uses traditional deterministic rules and does not invoke an AI model. The student must review, run, verify, and revise the project before accepting responsibility for the submitted work. The eventual report should describe the student's real Windows results and disclose this assistance.

Project repository: https://github.com/singhpingu/MSAI-631-A02-HCI

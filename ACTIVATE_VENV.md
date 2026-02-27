PowerShell venv activation troubleshooting

Problem:
- When running `.\.venv\Scripts\Activate` or `\.\venv\Scripts\activate` in PowerShell you may see:
  "execution of scripts is disabled on this system" and the venv does not activate. This causes the system Python to run and missing packages (e.g., `flask_cors`).

Quick options to fix or work around (pick one):

1) Allow running local activation scripts (recommended for dev)
- Run in PowerShell (CurrentUser scope, no admin required):

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate normally:

```powershell
cd D:\Catalogo
.\venv\Scripts\Activate.ps1
# now run
python app.py
```

2) Run the venv python directly (safe, no policy changes)
- Use the venv Python executable to run commands without activating:

```powershell
cd D:\Catalogo
.\venv\Scripts\python.exe app.py
# or run pytest
.\venv\Scripts\python.exe -m pytest
```

3) Use CMD activation if you prefer not to change PowerShell policy
- Open `cmd.exe` and run:

```cmd
D:\Catalogo> venv\Scripts\activate.bat
(venv) D:\Catalogo> python app.py
```

4) Temporary bypass (not persistent)
- In PowerShell you can run the activate script with the Bypass flag for a single command:

```powershell
powershell -ExecutionPolicy Bypass -NoProfile -Command "& '.\venv\Scripts\Activate.ps1'; python app.py"
```

Verification:
- When the server starts it prints the Python executable path. Confirm it shows the venv path like:

```
[startup] using python executable: D:\Catalogo\venv\Scripts\python.exe
```

- Also confirm there is no "flask_cors not installed" warning in the server output.

If you want, I can start the server in the background using the venv Python now and confirm the startup logs. If you'd like that, tell me to proceed or allow me to start it now.
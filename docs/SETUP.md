# Local Setup (Windows)

This guide gets your machine ready to develop and test the Lambdas locally.

---

## Step 1 — Install Python 3.11

We pin Python 3.11 because that's the runtime we use on Lambda. Mismatched versions cause subtle bugs.

1. Download from https://www.python.org/downloads/release/python-3118/ (pick **Windows installer (64-bit)**).
2. During install, **CHECK "Add python.exe to PATH"**.
3. Verify:

```cmd
python --version
```

Should print `Python 3.11.x`. If it doesn't, restart your terminal.

---

## Step 2 — Install Git

If you don't have it: https://git-scm.com/download/win

Verify:

```cmd
git --version
```

---

## Step 3 — Clone the repo

```cmd
cd C:\Users\<your-user>\path\to\your\workspace
git clone <repo-url>
cd project
```

If you don't have a repo set up yet, just navigate to the existing folder:

```cmd
cd "C:\Users\npach\OneDrive\Documentos\Claude\Projects\Cloud Computing\project"
```

---

## Step 4 — Create and activate a virtual environment

A `venv` keeps the project's Python packages isolated so they don't conflict with anything else on your system.

```cmd
python -m venv .venv
.venv\Scripts\activate
```

After activation your prompt should start with `(.venv)`. **You need to activate the venv every time you open a new terminal for this project.**

---

## Step 5 — Install dependencies

```cmd
pip install -r requirements.txt
```

This installs Pillow, Locust, pandas, matplotlib, and Jupyter. Takes 2–3 minutes.

Verify:

```cmd
python -c "import PIL, locust, pandas; print('OK')"
```

---

## Step 6 — Generate test images

```cmd
cd local-tests
python generate_images.py
cd ..
```

This creates 10 images in each size folder:
- `local-tests\images\small\` — around 100 KB each (500×500 px)
- `local-tests\images\medium\` — around 1 MB each (1500×1500 px)
- `local-tests\images\large\` — around 5 MB each (3000×3000 px)

---

## Step 7 — Verify local Lambda code runs

Pick the operation that's yours and run its local test:

```cmd
python local-tests\test_resize.py
python local-tests\test_grayscale.py
python local-tests\test_edge.py
```

Each script reads `images\medium\image_001.jpg`, runs the corresponding handler, and saves the result as `output_<op>.jpg` in the `local-tests\` folder.

Open the output file with any image viewer. It should look like the expected operation worked.

---

## Common issues

**"python is not recognized"** → PATH wasn't set. Reinstall Python with "Add to PATH" checked, OR add it manually to System Environment Variables.

**"Pillow import error"** → venv not activated. Run `.venv\Scripts\activate` again.

**Permission errors when activating venv** → run PowerShell as administrator once and execute: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.

**Can't generate images** → check write permissions on `local-tests\images\`. Try running terminal as administrator.

---

## Next step

Once everything above works, read `DEPLOY.md` to push your Lambda to AWS.

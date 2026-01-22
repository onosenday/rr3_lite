---
description: Setup the environment for RR3 Bot Lite
---

# Setup Workflow (Lite)

## Option 1: Automatic (Linux)
The `run.sh` script handles setup automatically.
```bash
chmod +x run.sh
./run.sh
```

## Option 2: Manual (Linux)

1.  Create virtual environment in project root:
    ```bash
    python3 -m venv venv
    ```

2.  Activate it:
    ```bash
    source venv/bin/activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

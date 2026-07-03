# Contributing

Thanks for helping improve **Staring Contest Final Boss**.

This project is an Open Sauce exhibit prototype, so reliability and clarity matter more than flashy changes.

## Good Contributions

- Bug fixes that keep the current gameplay intact.
- Webcam/blink detection reliability improvements.
- Menu and UI polish.
- Documentation improvements.
- Screenshot or demo GIF updates.
- Small tuning changes with clear before/after notes.

## Before You Change Code

Please check:

1. Does the change affect blink detection?
2. Does SPACE fallback still work?
3. Does `python main.py` still run?
4. Do survival and rhythm modes still run directly?
5. Does the README need an update?

## Local Setup

```bash
python -m venv .venv
pip install -r requirements.txt
python main.py
```

On Windows PowerShell, activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Pull Request Checklist

- [ ] I tested `python main.py`.
- [ ] I tested SPACE fallback if input behavior changed.
- [ ] I avoided unrelated gameplay changes.
- [ ] I updated docs if user-facing behavior changed.
- [ ] I did not add hardware behavior unless requested.


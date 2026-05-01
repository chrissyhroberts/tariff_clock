# Tariff Clock

A lightweight desktop app for tracking project time against a fixed allocation.

Designed for consulting, research support, and internal services where work is billed or monitored against a predefined time “tariff”.

---

## Features

- Multiple projects, each with a fixed time allocation
- Start/stop timers per project (chess-clock behaviour)
- Live countdown of remaining time
- Session tracking with automatic logging
- Manual time adjustments (+/- hours/minutes) with justification
- Full audit log per project (CSV-based)
- Editable history for correcting mistakes
- Clean, minimal interface with visual state highlighting

---

## How It Works

Each project has its own CSV file.

The app:

- Tracks remaining time
- Logs each session when stopped
- Stores a full audit trail of:
  - start time
  - end time
  - duration
  - user-entered summary
  - any manual adjustments

---

## Installation (macOS)

1. Download the `.zip` from Releases
2. Unzip it
3. Move `tariff_clock.app` somewhere convenient (e.g. Desktop or Applications)

---

## First Run (Important)

macOS will block the app initially because it is not signed.

To open:

1. Right-click on `tariff_clock.app`
2. Click **Open**
3. Click **Open** again in the dialog

After this, it will run normally.

---

## Data Storage

All project data is stored locally at:   
~/Documents/tariff_clock_projects

Each project has its own CSV file.

You can back these up, edit them, or move them between machines.

---

## Creating Projects

Projects are created automatically when a new CSV is added to the folder.

Basic format:  
	project_name,remaining_seconds  
	Project A,108000

(108000 seconds = 30 hours)

---

## Usage

- Click ▶ to start a project
- Click ■ to stop (you will be prompted for a summary)
- Starting another project automatically stops the current one
- Use +1h / -1h / +1m / -1m to adjust time (requires justification)
- Scroll to view full project history

---

## Editing Logs

Logs are stored as CSV and can be:

- edited directly in the app
- or modified manually in Excel/R

All edits should preserve the audit structure.

---

## Limitations

- Not code-signed or notarised (macOS warning on first run)
- Built for Apple Silicon (M1/M2/M3 Macs)
- No cloud sync (local files only)

---

## Roadmap (Planned)

- Export summaries / reports
- Backup and restore tools
- Improved audit integrity (edit tracking)
- Cross-platform builds (Windows/Linux)

---

## License

MIT License

Copyright (c) 2026 Chrissy Roberts

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
---

## Author

Chrissy Roberts,  LSHTM Global Health Analytics


---

## Notes

This tool is designed to be:

- transparent (CSV-based)
- auditable (no hidden state)
- low-friction (no install, no dependencies)

If something breaks, your data is still intact.

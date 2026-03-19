# clasp Workflow Reference

## Installation & Authentication

```bash
npm install -g @google/clasp
clasp login          # OAuth browser flow; stores creds in ~/.clasprc.json
clasp logout
```

## Project Setup

### New Project
```bash
clasp create --title "My Script"  # Creates .clasp.json + appsscript.json
clasp create --type sheets        # Create bound to a new Sheet
clasp create --type docs          # Create bound to a new Doc
clasp create --type slides        # Create bound to a new Presentation
clasp create --type forms         # Create bound to a new Form
clasp create --type webapp        # Standalone web app
clasp create --type api           # API executable
```

### Clone Existing Project
```bash
clasp clone <scriptId>            # Clone by script ID
clasp clone <scriptId> --rootDir src  # Clone into src/ subdirectory
```

**Finding the Script ID:** Open the script in the Apps Script editor → Project Settings → Script ID.

## Key Config Files

### `.clasp.json`
```json
{
  "scriptId": "1abc123...",
  "rootDir": "src"
}
```
- `scriptId`: Links local directory to the remote Apps Script project
- `rootDir`: Optional source directory (keeps config separate from code)
- Consider `.gitignore`-ing this if the scriptId is sensitive

### `appsscript.json` (Manifest)
```json
{
  "timeZone": "America/New_York",
  "dependencies": {
    "libraries": [],
    "enabledAdvancedServices": []
  },
  "exceptionLogging": "STACKDRIVER",
  "runtimeVersion": "V8",
  "oauthScopes": [
    "https://www.googleapis.com/auth/spreadsheets.readonly"
  ],
  "webapp": {
    "executeAs": "USER_DEPLOYING",
    "access": "ANYONE"
  }
}
```

**Always review this file before pushing.** Check:
- `oauthScopes` — are they the narrowest possible?
- `runtimeVersion` — should be `"V8"` for modern JS
- `timeZone` — correct for the use case?
- `webapp` settings — `executeAs` and `access` appropriate?

## Daily Development Commands

```bash
clasp pull                  # Download remote → local (overwrites local!)
clasp push                  # Upload local → remote (overwrites remote!)
clasp push --watch          # Auto-push on file save
clasp status                # Show which files will be pushed
clasp open                  # Open in Apps Script editor
clasp logs                  # Show recent execution logs
clasp logs --watch          # Tail logs
```

### Pull vs Push — Direction Matters!

| Command | Direction | Overwrites |
|---------|-----------|-----------|
| `clasp pull` | Remote → Local | **Local files** |
| `clasp push` | Local → Remote | **Remote files** |

**Always pull first if someone may have edited in the browser.**

## Versioning & Deployment

```bash
# Create immutable version snapshot
clasp version "v1.0 — initial release"

# List versions
clasp versions

# Deploy a specific version
clasp deploy --versionNumber 1 --description "Production v1.0"

# Update existing deployment to new version
clasp deploy --deploymentId AKfycbx... --versionNumber 2

# List deployments
clasp deployments

# Remove a deployment
clasp undeploy <deploymentId>
```

### Deployment Workflow

```
1. Develop and test locally
2. clasp push                                    (upload code)
3. Test with head deployment (/dev URL)
4. clasp version "v1.0 — description"            (freeze snapshot)
5. clasp deploy --versionNumber 1 --description "Production v1.0"
6. Share the /exec URL (not /dev) with users
7. For updates: edit → push → test → version → deploy to same ID
```

### Head vs Versioned Deployment

| | Head (dev) | Versioned (exec) |
|---|-----------|-----------------|
| URL suffix | `/dev` | `/exec` |
| Code | Always latest saved | Frozen at version |
| Use for | Testing | Production |
| Updates automatically | Yes | No (must redeploy) |

## Remote Execution

```bash
# Run a function remotely (requires Apps Script API enabled in GCP)
clasp run myFunction
clasp run myFunction --params '[1, "hello"]'
```

**Prerequisites for `clasp run`:**
1. GCP project linked to the script
2. Apps Script API enabled in GCP Console
3. OAuth credentials set up
4. Function must exist in a deployment

## Directory Structure

clasp preserves directory structure. Local `src/utils/helpers.js` becomes `utils/helpers` in the Apps Script editor.

Recommended project layout:
```
my-script/
├── .clasp.json              # Script ID, rootDir
├── .gitignore               # Include .clasp.json if scriptId is sensitive
├── appsscript.json          # Manifest (or in rootDir)
└── src/                     # rootDir if configured
    ├── Code.js              # Main entry point
    ├── Triggers.js          # Trigger handlers
    ├── Utils.js             # Shared utilities
    └── sidebar.html         # HTML for sidebars/dialogs
```

## Ignoring Files

Create `.claspignore` (same syntax as `.gitignore`) to exclude files from push:
```
# .claspignore
node_modules/**
tests/**
*.test.js
README.md
```

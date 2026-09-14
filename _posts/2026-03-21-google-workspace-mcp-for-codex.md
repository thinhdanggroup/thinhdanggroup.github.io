---
author:
    name: "Thinh Dang"
    avatar: "/assets/images/avatar.png"
    bio: "Experienced Fintech Software Engineer Driving High-Performance Solutions"
    location: "Viet Nam"
    email: "thinhdang206@gmail.com"
    links:
        -   label: "Linkedin"
            icon: "fab fa-fw fa-linkedin"
            url: "https://www.linkedin.com/in/thinh-dang/"
toc: true
toc_sticky: true
header:
    overlay_image: /assets/images/google-workspace-mcp-for-codex/banner.webp
    og_image: /assets/images/google-workspace-mcp-for-codex/og.jpg
    overlay_filter: 0.5
    teaser: /assets/images/google-workspace-mcp-for-codex/teaser.webp
title: "Connecting Codex to Google Workspace via MCP"
tags:
    - Developer Tools
    - MCP

categories:
    - infrastructure
description: "When you work with an AI coding agent like Codex, the real productivity gains come from letting it interact with the systems around your code — not just the…"
---

When you work with an AI coding agent like Codex, the real productivity gains come from letting it interact with the systems around your code — not just the code itself. Connecting Codex to Google Workspace via the **Model Context Protocol (MCP)** lets it search Gmail, read messages, download attachments, manage drafts, and access Calendar, Drive, Docs, Sheets, and more — all within a single conversation session.

Without a stable MCP setup, you end up copy-pasting context between tools, breaking your flow. In this post, we will walk through the recommended setup for Google Workspace MCP with Codex, covering installation, OAuth authentication, available tools, and how to troubleshoot common failures.

> **Version note:** This guide was verified on March 20, 2026 using Google Workspace MCP `v0.0.7` (released March 11, 2026).

## Why a Pinned Local Install

The most common approach people try first is running the MCP server via `npx` at runtime. This works for quick experiments but causes two problems in practice:

- **Version drift** — `npx` fetches the latest release every time Codex starts, so a server update can silently break your configured tool names or OAuth flow.
- **Cold start latency** — downloading and compiling on each session adds startup time that disrupts the agent loop.

The reliable alternative is to clone a pinned release locally, build it once, and point Codex at the compiled `dist/index.js` entrypoint. This gives you a stable path in `~/.codex/config.toml` and a predictable server version until you explicitly choose to upgrade.

## Prerequisites

Before starting, make sure you have:

- Codex CLI with MCP support enabled
- Node.js and npm installed
- A Google account with access to the Workspace data you want Codex to use
- A browser available for the OAuth flow
- A terminal with access to macOS Keychain, or file-storage fallback if Keychain is unavailable

## Setup

### Step 1: Remove Any Existing Google Workspace MCP Entry

If you previously experimented with a Gmail or Workspace MCP entry, remove it first to avoid conflicts:

```bash
codex mcp remove google_workspace
```

If the server was never configured, this command will fail — that is expected. Continue to the next step.

### Step 2: Clone a Pinned Copy

We pin to `v0.0.7` to ensure a stable, tested build. Clone it into `~/.codex/vendor` to keep it separate from your project code:

```bash
mkdir -p ~/.codex/vendor
git clone --branch v0.0.7 --depth 1 \
  https://github.com/gemini-cli-extensions/workspace.git \
  ~/.codex/vendor/google-workspace
```

The `--depth 1` flag fetches only the tagged commit, keeping the download small.

### Step 3: Build the Server

Run both build steps from the cloned directory:

```bash
cd ~/.codex/vendor/google-workspace
npm install
npm run build:auth-utils -w workspace-server
```

`npm install` compiles the main MCP server. The `build:auth-utils` step compiles the headless login helper you will use in the next step. Both are required — skipping the second step means the OAuth login command will not be available.

### Step 4: Add the MCP Server to Codex Config

Edit `~/.codex/config.toml` and add the following block, replacing `<your-user>` with your actual macOS username:

```toml
[mcp_servers.google_workspace]
command = "node"
args = ["/Users/<your-user>/.codex/vendor/google-workspace/workspace-server/dist/index.js", "--debug", "--use-dot-names"]
cwd = "/Users/<your-user>/.codex/vendor/google-workspace"
```

The `--use-dot-names` flag is important — it exposes tool names in the `gmail.search` format rather than underscore variants, which is what most prompts and docs reference.

### Step 5: Authenticate via OAuth

Run the headless login helper:

```bash
cd ~/.codex/vendor/google-workspace
node scripts/auth-utils.js login
```

The helper prints a Google OAuth URL. Complete the flow:

1. Open the URL in your browser.
2. Sign in to the Google account you want Codex to use.
3. Approve the requested Workspace scopes.
4. Copy the credentials JSON shown by the browser.
5. Paste it into the terminal and press Enter twice.

The credentials are saved to macOS Keychain (or an encrypted file if Keychain is unavailable).

### Step 6: Verify Authentication

Confirm both tokens were saved:

```bash
cd ~/.codex/vendor/google-workspace
node scripts/auth-utils.js status
```

A successful result shows both an access token and a refresh token marked as present. If either is missing, re-run the login step.

### Step 7: Restart Codex

Start a new Codex session so the new MCP server is loaded. Then confirm it registered correctly:

```bash
codex mcp get google_workspace
codex mcp list
```

You should see `google_workspace` in the list with its tools enumerated.

## Available Gmail Tools

Once connected, Codex can use the following Gmail tools within the MCP session:

| Tool | Purpose |
|------|---------|
| `gmail.search` | Search messages by query string |
| `gmail.get` | Read a specific message by ID |
| `gmail.downloadAttachment` | Download an attachment from a message |
| `gmail.send` | Send a new email |
| `gmail.createDraft` | Create a draft without sending |
| `gmail.sendDraft` | Send a previously created draft |
| `gmail.modify` | Add or remove labels on a message |
| `gmail.batchModify` | Modify labels on multiple messages |
| `gmail.modifyThread` | Modify labels on an entire thread |
| `gmail.listLabels` | List all labels in the account |
| `gmail.createLabel` | Create a new label |

Beyond Gmail, the same server exposes tools for Drive, Calendar, Docs, Sheets, Slides, Chat, and People — all accessible from a single MCP connection.

## Troubleshooting

### Status Says "No Credentials Found" After Login

This typically means the `status` command ran in a different process context than where the credentials were saved — most commonly a sandboxed terminal or IDE terminal that cannot access the same Keychain backend.

Re-run the status check from a standard macOS terminal (Terminal.app or iTerm2), not from within an IDE or restricted shell. If the problem persists, switch to file-based storage (see below).

### `/dev/tty` or Terminal Prompt Errors During Login

The headless login helper reads the pasted credentials JSON from a real terminal device. Sandboxed environments that block `/dev/tty` (some CI runners, restricted IDE terminals) will fail here.

Run the login command from a normal local terminal session, then verify with `status` before returning to your IDE.

### Keychain Is Unavailable

If macOS Keychain is not accessible, force the server to use encrypted file storage instead:

```bash
export GEMINI_CLI_WORKSPACE_FORCE_FILE_STORAGE=true
node scripts/auth-utils.js login
```

Set the same environment variable when checking status or starting the server later, so both operations use the same storage backend consistently.

### Server Does Not Appear in Codex

Check these three things in order:

1. The `[mcp_servers.google_workspace]` block exists in `~/.codex/config.toml`
2. The file `~/.codex/vendor/google-workspace/workspace-server/dist/index.js` exists
3. Codex was restarted after the config change

### Updating to a Newer Release

When a new version is available and you want to upgrade:

```bash
cd ~/.codex/vendor/google-workspace
git fetch --tags
git checkout v0.0.8   # replace with the target version
npm install
npm run build:auth-utils -w workspace-server
```

Re-run the OAuth login step after upgrading, as new releases may request additional scopes.

## Security Considerations

Before using this integration in day-to-day work, keep the following in mind:

- The MCP server authenticates as your Google account and can read and modify Gmail, Drive, Calendar, and other Workspace data.
- Only enable it in Codex sessions you trust — avoid shared or multi-user environments.
- The OAuth consent covers broad Workspace scopes, not only Gmail. Review what scopes are requested during login.
- Review write operations (send, createDraft, modify) carefully before approving them in the agent loop.
- Never paste live OAuth credentials into shared logs, tickets, or untrusted chat sessions.

## Conclusion

By following this setup, Codex gains persistent, stable access to Google Workspace without runtime dependency resolution or version surprises. The key decisions that make this reliable are:

- **Pinned local clone** — eliminates version drift between sessions
- **Pre-built dist artifact** — no compile step at agent startup
- **Headless OAuth helper** — runs outside the agent process to avoid sandbox restrictions
- **`--use-dot-names` flag** — exposes the standard `gmail.search`-style tool names

Start with `gmail.search` and `gmail.get` to validate the connection, then expand to the Drive and Calendar tools as your workflows demand.

## References

- Google MCP index: <https://github.com/google/mcp>
- Google Workspace MCP repo: <https://github.com/gemini-cli-extensions/workspace>
- Workspace extension manifest: <https://raw.githubusercontent.com/gemini-cli-extensions/workspace/main/gemini-extension.json>
- Workspace tool list: <https://raw.githubusercontent.com/gemini-cli-extensions/workspace/main/docs/index.md>

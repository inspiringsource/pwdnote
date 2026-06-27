# pwdNote

[![PyPI version](https://img.shields.io/pypi/v/pwdnote.svg)](https://pypi.org/project/pwdnote/)

**Encrypted, project-local notes for your terminal.**

`pwdnote` keeps project-specific notes — TODOs, deployment notes, AWS account
details, session IDs, customer context, reminders — encrypted on disk, right
next to your code, without ever exposing plaintext inside the repository.

It is **local-first**, **encrypted-by-default**, **Git-friendly**, and
**terminal-native**. The single encrypted file (`.pwdnote.enc`) is safe to
commit; without your key it is just ciphertext.

`pwdnote` started as a simple way to keep personal project notes close to my code, without worrying about accidentally committing secrets or overcomplicating the workflow.

## Demo

![pwdnote demo](https://raw.githubusercontent.com/inspiringsource/pwdnote/main/demo/shortDemo.gif)

A companion [VS Code extension](https://marketplace.visualstudio.com/items?itemName=inspiringsource.pwdnote-vscode) is also available.

---

## Installation

```bash
uv tool install pwdnote
```

That's it — no further setup. The encryption key is generated automatically on
first use.

---

## VS Code Extension

The official **pwdnote** VS Code extension provides a graphical interface for
the CLI. It lets you:

- open project notes directly from VS Code
- edit encrypted notes without leaving the editor
- initialize new project notes
- add quick notes
- view project status

The extension uses the `pwdnote` CLI for all encryption and decryption, so the
same encrypted files work seamlessly from both the terminal and VS Code.

- Marketplace: <https://marketplace.visualstudio.com/items?itemName=inspiringsource.pwdnote-vscode>
- Source: <https://github.com/inspiringsource/pwdnote-vscode>

---

## Quick start

```bash
cd my-project
pwdnote init                                  # create .pwdnote.enc
pwdnote edit                                  # open it in your editor
pwdnote                                        # print the decrypted note
pwdnote add "Remember to rotate AWS credentials" # appends a new line
```

---

## Commands

| Command | Description |
| --- | --- |
| `pwdnote` | Show the decrypted project note. |
| `pwdnote init` | Create an encrypted note (`# Project Notes`). |
| `pwdnote edit` | Decrypt, open in `$VISUAL`/`$EDITOR`, re-encrypt on save. |
| `pwdnote add "text"` | Append `- text` to the note without opening an editor. |
| `pwdnote head` | Print the first 10 lines of the decrypted note. |
| `pwdnote head -n 5` | Print the first 5 lines of the decrypted note. |
| `pwdnote tail` | Print the last 10 lines of the decrypted note. |
| `pwdnote tail -n 5` | Print the last 5 lines of the decrypted note. |
| `pwdnote status` | Show the project root, note file, and encryption status. |
| `pwdnote gitignore` | Add recommended ignore entries (`.pwdnote.tmp`, `.pwdnote.cache`). |
| `pwdnote key path` | Print the key file path. |
| `pwdnote key export` | Print the key to stdout for backup or transfer. |
| `pwdnote key import` | Import a key from stdin. |
| `pwdnote config path` | Print the config file path. |
| `pwdnote config show` | Print the effective configuration. |
| `pwdnote config init` | Create `config.toml` with defaults. |

### Aliases

Short built-in aliases are available for the most common commands:

| Alias | Command |
| --- | --- |
| `pwdnote i` | `pwdnote init` |
| `pwdnote e` | `pwdnote edit` |
| `pwdnote a` | `pwdnote add` |
| `pwdnote s` | `pwdnote status` |

---

## Note previews

Use `head` and `tail` to preview only part of a decrypted project note:

```bash
pwdnote head
pwdnote head --lines 5
pwdnote tail
pwdnote tail -n 5
```

These commands print plaintext note content to stdout without extra formatting.

---

## Key management

The file key backend stores your encryption key at `~/.config/pwdnote/key`,
honouring `XDG_CONFIG_HOME`. The key file is created with `0600` permissions
inside a `0700` config directory.

Show the current key path:

```bash
pwdnote key path
```

Export the key for backup or another trusted device:

```bash
pwdnote key export > pwdnote-key.backup
```

Import the key on another trusted device:

```bash
cat pwdnote-key.backup | pwdnote key import
```

Replace an existing key only when you intend to:

```bash
cat pwdnote-key.backup | pwdnote key import --force
```

Losing the key means losing access to encrypted notes. Anyone with the key can
decrypt your notes, so store backups in a trusted password manager or another
secure location.

---

## Configuration

Configuration is optional. With no config file the defaults apply and behaviour
is unchanged.

The config file lives at `~/.config/pwdnote/config.toml` (honouring
`XDG_CONFIG_HOME`). Run `pwdnote config init` to create it with the defaults:

```toml
[notes]
initial_content = "# Project Notes\n"
auto_gitignore_note_file = false

[editor]
command = ""

[security]
key_backend = "file"
```

- `notes.initial_content` — content used by `pwdnote init` for a new note.
- `notes.auto_gitignore_note_file` — when `true`, `pwdnote init` adds
  `.pwdnote.enc` to `.gitignore`.
- `editor.command` — when set, overrides `$VISUAL` / `$EDITOR`.
- `security.key_backend` — only `file` is supported today. Other values fail
  with a clear error; advanced key backends may come later.

---

## Project root detection

`pwdnote` does not operate only on the current directory. Starting from your
working directory it searches **upward**:

1. If `.pwdnote.enc` exists, that location is used.
2. Otherwise, if `.git` exists, that location is treated as the project root.
3. The search stops at the filesystem root.

So from `project/backend/api`, running `pwdnote` finds
`project/.pwdnote.enc`.

---

## Editor integrations

`pwdnote` exposes a few non-interactive commands for tools such as a VS Code
extension:

| Command | Purpose |
| --- | --- |
| `pwdnote read` | Print the decrypted note to stdout (no formatting). |
| `pwdnote write --stdin` | Replace the note with content from stdin (add `--create` to create it). |
| `pwdnote root` | Print the detected project root. |
| `pwdnote note-path` | Print the resolved `.pwdnote.enc` path. |

These write machine-readable output to stdout and errors to stderr. Encryption
is always handled by the CLI, so integrations never touch the key or the file
format. These are the commands that power the official
[VS Code extension](https://marketplace.visualstudio.com/items?itemName=inspiringsource.pwdnote-vscode).

---

## About the `.pwdnote.enc` file in this repository

This repository intentionally includes a `.pwdnote.enc` file.

The file contains real project note data encrypted by `pwdnote`. It is included to demonstrate one of the core design goals of the tool: project notes can be stored alongside source code and committed to Git while remaining encrypted on disk.

The repository stores only ciphertext. Without the corresponding encryption key, the contents cannot be read.

By default, `.pwdnote.enc` is designed to be commit-safe. If you prefer not to commit your project notes, you can manually add `.pwdnote.enc` to your `.gitignore` or use `pwdnote gitignore` to add it automatically.

---

## Security model

- **Authenticated encryption.** Notes are encrypted with
  [Fernet](https://cryptography.io/en/latest/fernet/) (AES-128-CBC with an
  HMAC-SHA256 authentication tag) from the well-maintained `cryptography`
  library. We do not implement custom cryptography.
- **Integrity protection.** Tampered or corrupted files fail to decrypt rather
  than returning garbage.
- **Key storage.** A single key is generated on first use and stored at
  `~/.config/pwdnote/key` (honouring `XDG_CONFIG_HOME`) with `0600`
  permissions inside a `0700` directory.
- **No plaintext on disk.** `pwdnote edit` writes to a temporary file with
  restrictive permissions and always deletes it afterwards.
- **Commit-safe.** `.pwdnote.enc` is meant to be committed; it is ciphertext.
  Do **not** ignore it. (The temporary/cache artifacts are ignored instead.)

The crypto backend lives behind a small abstraction (`encrypt_text` /
`decrypt_text`), so it can be replaced later — and future versions may add
macOS Keychain, 1Password, `age`, or GPG key backends.

---

## Limitations

- The key lives on your machine. If you lose `~/.config/pwdnote/key`, encrypted
  notes cannot be recovered. Back the key up somewhere safe.
- There is no built-in sync. Sharing a note across machines means sharing the
  same key (e.g. via a secrets manager).
- One note per project root. `pwdnote` is intentionally simple — no databases,
  no cloud, no plugins, no AI features.
- The VS Code extension is simply another frontend for the CLI. It shares the
  same encryption key and note format, so it adds no separate storage or
  security model.

---

## Contributing

```bash
git clone https://github.com/inspiringsource/pwdnote
cd pwdnote
uv sync                 # install deps + dev tools
uv run pytest           # run the test suite
uv run pwdnote --help   # try the CLI from source
```

Issues and pull requests are welcome. Please keep the tool small and reliable —
new storage/key backends should slot in behind the existing abstractions.

---

## License

[MIT](LICENSE)

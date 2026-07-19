# pwdNote

[![PyPI version](https://img.shields.io/pypi/v/pwdnote.svg)](https://pypi.org/project/pwdnote/)

**Encrypted, project-local notes for your terminal.**

`pwdnote` keeps encrypted project notes — deployment notes, reminders,
troubleshooting notes, architecture notes, customer context, TODOs, session
information, feature flags, and infrastructure reminders — on disk, right next
to your code, without exposing plaintext inside the repository.

It is intended for notes about systems and project work. It is not a password
manager, and it is not a replacement for enterprise secrets-management systems.

It is **local-first**, **encrypted-by-default**, **Git-friendly**, and
**terminal-native**. The single encrypted file (`.pwdnote.enc`) is safe to
commit; without your key it is just ciphertext.

`pwdnote` started as a simple way to keep personal project notes close to my code, without worrying about accidentally committing plaintext notes or overcomplicating the workflow.

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
pwdnote add "Restart the worker after deployment" # appends a new line
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
| `pwdnote cat 1` | Print the first Markdown list item without its `- ` marker. |
| `pwdnote copy 1` | Copy the first Markdown list item to the system clipboard. |
| `pwdnote paste 1` | Insert the first Markdown list item into the Zsh command line. |
| `pwdnote shell install` | Install the optional Zsh integration used by `paste`. |
| `pwdnote log` | Show commits where `.pwdnote.enc` changed. |
| `pwdnote show HEAD~1` | Decrypt and print the note from a Git revision. |
| `pwdnote diff HEAD~1 HEAD` | Show a readable diff between two encrypted note revisions. |
| `pwdnote diff` | Compare the committed note with the working tree note. |
| `pwdnote status` | Show the project root, note file, and encryption status. |
| `pwdnote stats` | Summarize note content, storage, security, and Git history. |
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
| `pwdnote c` | `pwdnote cat` |
| `pwdnote y` | `pwdnote copy` |
| `pwdnote p` | `pwdnote paste` |

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

## Reuse individual list items

Notes added with `pwdnote add` are stored as Markdown list items.

Preview an item:

```bash
pwdnote cat 2
```

Copy it to the system clipboard:

```bash
pwdnote copy 2
```

Install the optional Zsh integration and insert it into the next Zsh prompt:

```bash
pwdnote shell install
source ~/.zshrc
pwdnote paste 2
```

After `pwdnote paste 2`, the selected text appears in the next Zsh command line.
It is ready for review or editing and is not executed automatically.

Short aliases are also available:

```bash
pwdnote c 2
pwdnote y 2
pwdnote p 2
```

Numbering is 1-based; `one` and `first` select the first item. Direct insertion
currently supports Zsh. Clipboard copying remains cross-platform, and the shell
integration is optional: `cat` and `copy` work without it. None of these
commands execute the stored content.

`pwdnote shell install` writes the generated integration to
`~/.config/pwdnote/shell/pwdnote.zsh` (honouring `XDG_CONFIG_HOME`) and adds one
managed source block to `~/.zshrc`. Inspect or remove it with:

```bash
pwdnote shell status
pwdnote shell print
pwdnote shell uninstall
```

`shell status` exits with status 1 when either installation piece is missing or
out of date.

---

## Note statistics

`pwdnote stats` reports the project and note paths, plaintext line, word, and
character counts, encrypted file size, and the active encryption and key
backends. It also includes the revision count and first/latest commit dates for
`.pwdnote.enc` when Git history is available.

```bash
pwdnote stats
```

---

## Readable Git history

GitHub and normal Git diffs show `.pwdnote.enc` as ciphertext. Because
`pwdnote` has access to your local key, it can decrypt historical versions
locally and show readable history without writing plaintext to disk.

```bash
pwdnote log
pwdnote show HEAD~1
pwdnote diff HEAD~1 HEAD
pwdnote diff
```

`pwdnote diff` compares the `HEAD` version of `.pwdnote.enc` with the working
tree version. `pwdnote diff HEAD~1 HEAD` compares two committed versions.

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

Handle exported keys like passwords. Anyone with the exported key can decrypt
the associated notes.

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

`pwdnote` encrypts notes on disk. The encrypted `.pwdnote.enc` file is designed
to be safely committed to Git, but anyone with both that file and the
corresponding key can decrypt it. The primary goal is protecting project notes
when repositories are shared or stored remotely; `pwdnote` is not designed to
replace dedicated secrets-management tools.

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

By default, `pwdnote` uses one local encryption key. Multiple projects have
separate encrypted note files, but they share the same local key. This keeps
the tool simple and makes backup straightforward; future releases may support
additional key backends.

---

## FAQ

### Can I commit `.pwdnote.enc`?

Yes. `.pwdnote.enc` is designed to be committed because it contains encrypted
data, not plaintext notes. Keep the corresponding key private.

### Is pwdnote a password manager?

No. `pwdnote` is intended for encrypted project notes, not for managing
passwords or production secrets.

---

## Limitations

- The key lives on your machine. If you lose `~/.config/pwdnote/key`, encrypted
  notes cannot be recovered. Back the key up somewhere safe.
- There is no built-in sync. Sharing a note across machines means sharing the
  same key through a trusted backup or transfer method.
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

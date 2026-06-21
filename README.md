# pwdnote

**Encrypted, project-local notes for your terminal.**

`pwdnote` keeps project-specific notes — TODOs, deployment notes, AWS account
details, session IDs, customer context, reminders — encrypted on disk, right
next to your code, without ever exposing plaintext inside the repository.

It is **local-first**, **encrypted-by-default**, **Git-friendly**, and
**terminal-native**. The single encrypted file (`.pwdnote.enc`) is safe to
commit; without your key it is just ciphertext.

`pwdnote` is *not* a cloud service, a note-taking app, a password manager, a
database, or a sync platform. It does one small thing well.

---

## Installation

```bash
uv tool install pwdnote
```

That's it — no further setup. The encryption key is generated automatically on
first use.

---

## Quick start

```bash
cd my-project
pwdnote init                                  # create .pwdnote.enc
pwdnote edit                                  # open it in your editor
pwdnote                                        # print the decrypted note
pwdnote add "Remember to rotate AWS credentials"
```

---

## Commands

| Command | Description |
| --- | --- |
| `pwdnote` | Show the decrypted project note. |
| `pwdnote init` | Create an encrypted note (`# Project Notes`). |
| `pwdnote edit` | Decrypt, open in `$VISUAL`/`$EDITOR`, re-encrypt on save. |
| `pwdnote add "text"` | Append `- text` to the note without opening an editor. |
| `pwdnote status` | Show the project root, note file, and encryption status. |
| `pwdnote gitignore` | Add recommended ignore entries (`.pwdnote.tmp`, `.pwdnote.cache`). |

### Examples

```bash
$ pwdnote
TODO:
- rotate AWS keys
- update deployment docs
Notes:
Client requested staging environment.

$ pwdnote status
Project root:
  ~/projects/example
Note file:
  .pwdnote.enc
Encrypted:
  Yes
```

If no note exists yet:

```
No project note found.
Run:
  pwdnote init
```

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

---

## Contributing

```bash
git clone https://github.com/pwdnote/pwdnote
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

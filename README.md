# gdoc-vim

Edit **Google Docs as Markdown** in your terminal editor.

Google Docs speaks Markdown natively (both export and import), so a document can
be round-tripped through a local `.md` file. `gdoc-vim` makes that one command:

```bash
gdoc-vim https://docs.google.com/document/d/FILE_ID/edit
```

It pulls the doc as Markdown, opens it in `vim` (or your `$EDITOR`), and on save
converts it back and pushes it to the same document — preserving its link,
sharing settings, and revision history.

---

## Install

Install straight from GitHub:

```bash
pipx install git+https://github.com/gmajian/gdoc-vim
```

Once published to PyPI, this works too:

```bash
pipx install gdoc-vim
```

Either way you get a `gdoc-vim` command on your `PATH`. pipx keeps the tool in
its own virtualenv and links the executable into `~/.local/bin`; if that
directory isn't on your `PATH` yet, run `pipx ensurepath` once and restart your
shell.

`pip install` works as well, but pipx is preferred for command-line tools since
it avoids polluting your Python environment.

The first time you run a command, gdoc-vim checks whether it can reach your
Google account and walks you through anything that's missing:

- **No OAuth client configured?** It prints step-by-step setup instructions,
  naming the exact path to save the file to.
- **Not signed in yet?** A browser opens once to authorize, and the token is
  cached at `~/.config/gdoc-vim/token.json`.

**There is no separate login step** — just run the tool and follow the prompts.

> While setting up your OAuth client, also set its publishing status to **In
> production**. Clients left in *Testing* get refresh tokens that expire after
> 7 days, which means signing in again every week. See
> [Avoid the 7-day re-authorization trap](#avoid-the-7-day-re-authorization-trap).

## Usage

```bash
# Edit an existing doc (URL or bare id; extra URL params like ?tab=t.0 are fine)
gdoc-vim https://docs.google.com/document/d/FILE_ID/edit?tab=t.0

# Create a new doc and start editing it immediately
gdoc-vim -n "Meeting notes"

# Rename a doc (no editor)
gdoc-vim <url> -t "Better title"

# Rename and edit in one go
gdoc-vim <url> -t "Better title" -e

# Review a diff and confirm before uploading
gdoc-vim <url> -c

# Non-interactive: export to / import from a local file
gdoc-vim <url> -o notes.md      # export only
gdoc-vim <url> -p notes.md      # overwrite the doc from notes.md

# Sign in as a different account
gdoc-vim <url> --reauth
```

Saving in the editor uploads immediately. Pass `-c/--confirm` if you'd rather
see a diff and approve it first.

### Choosing the editor

`gdoc-vim` uses, in order: `$GDOC_VIM_EDITOR`, `$VISUAL`, `$EDITOR`, then `vim`.
The value may include arguments, e.g. `export GDOC_VIM_EDITOR="code --wait"`.

---

## Why you create your own OAuth client

Talking to the Drive API requires an OAuth **client** — an app identity issued
by Google. gdoc-vim asks you to create one rather than shipping a shared one,
and that is a deliberate trade-off worth explaining.

gdoc-vim needs the full `drive` scope, because it opens and overwrites documents
the app did not create (any doc you paste a URL for). Google classifies `drive`
as a **restricted scope**, the most tightly controlled tier. Shipping a shared
client that anyone could use would require the app to pass Google's
[restricted scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification),
which mandates a third-party **CASA security assessment**, repeated **at least
every 12 months**. That is aimed at commercial services handling user data at
scale, and is not a reasonable burden for a free command-line tool.

Creating your own client takes about three minutes, and gdoc-vim walks you
through it the first time you run it. Your credentials stay yours: your data is
never routed through anyone else's Google project.

### Avoid the 7-day re-authorization trap

By default a new OAuth client has publishing status **Testing**, and Google
issues refresh tokens that **expire after 7 days** for clients in that state.
You would have to sign in again every week.

To fix it, open the Google Cloud Console, go to the OAuth consent screen
(newer console: **Google Auth Platform → Audience**) and set the publishing
status to **In production**.

This does *not* require verification. Because the app is unverified, you will
see a warning screen at sign-in — click **Advanced → Go to gdoc-vim (unsafe)**
once. In exchange, your login stops expiring. Unverified apps are subject to a
user cap (around 100), which is ample for personal use.

### Optional: bundling a client for a small group

If you want a handful of people — a team, a few friends — to install and run
gdoc-vim with no setup at all, you can ship a client with the package.

gdoc-vim resolves client credentials in this order:

1. `$GDOC_VIM_CLIENT_SECRETS` — path to a client secrets JSON
2. `~/.config/gdoc-vim/credentials.json` — per-user override
3. `src/gdoc_vim/client_secret.json` — bundled with the package

Place the downloaded JSON at `src/gdoc_vim/client_secret.json` before building.
It is `.gitignore`d, so inject it at release time (e.g. from a CI secret) rather
than committing it:

```bash
cp /path/to/downloaded.json src/gdoc_vim/client_secret.json
python -m build
twine upload dist/*
```

A Desktop-app client secret is **not** a confidential secret — Google's own
[docs](https://developers.google.com/identity/protocols/oauth2/native-app) note
that installed apps cannot keep one, which is why the flow does not depend on it
staying private. Keeping it out of git just makes it easy to rotate.

**Every person who signs in must be added to your client's user list**, and the
cap still applies. This works well for a known group; it does not scale to
strangers installing from PyPI, which is why the default path is for each user
to create their own client.

---

## Limitations

Markdown is a lossy representation of a Google Doc. The round trip preserves
headings, lists, bold/italic, links, code blocks, blockquotes, and simple
tables, but features with no Markdown equivalent may be **simplified or lost**:

- comments and suggested edits
- embedded drawings, charts, and equations
- images (behavior depends on Google's converter)
- fine-grained styling (fonts, colors, spacing)

**A push replaces the document's entire body.** Google keeps full revision
history, so you can restore a previous version via **File → Version history** in
the Docs UI if a conversion surprises you. Try the tool on a copy of anything
important first.

## Development

The package lives under `src/`, so an editable install is the easiest way to
work on it:

```bash
python3 -m venv .venv
./.venv/bin/pip install -e .
./.venv/bin/gdoc-vim --help
```

## License

GNU General Public License v3.0 or later — see [LICENSE](LICENSE).

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version. It is distributed WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

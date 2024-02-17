# systemd-language-server

Language server for systemd unit files.

## Supported Features

### `textDocument/completion`

Completion for

- unit file directives
- unit file sections
<!-- - values of some directives -->

### `textDocument/hover`

Documentation for directives supplied on hovering.

## Installation

```
pip install systemd-language-server
```

## Integrations

### coc.nvim

In `coc-settings.json`, under `.languageserver`:

```json
...
"systemd-language-server": {
  "command": "systemd-language-server",
  "filetypes": ["systemd"]
}
...
```

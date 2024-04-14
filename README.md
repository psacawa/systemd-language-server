# systemd-language-server

[![PyPI](https://img.shields.io/pypi/v/systemd-language-server)](https://pypi.org/project/systemd-language-server)
[![GitHub Actions (Tests)](https://github.com/psacawa/systemd-language-server/actions/workflows/test.yml/badge.svg)](https://github.com/psacawa/systemd-language-server/actions)
[![GitHub](https://img.shields.io/github/license/psacawa/systemd-language-server)](https://github.com/psacawa/systemd-language-server/blob/master/LICENSE)

Language server for systemd unit files. Result of an exercise to learn the language server protocol.

## Supported Features

### `textDocument/completion`

Completion for

- unit file directives
- unit file sections
<!-- - values of some directives -->

![](assets/completion.gif)

### `textDocument/hover`

Documentation for directives supplied on hovering.

![](assets/hover.gif)

For markup in hover windows (i.e. the fancy highlighting), `pandoc` must be found in `$PATH`. Otherwise, there will be fallback to plain text.

## Installation

```
pip install systemd-language-server
```

## Example Integrations

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

### nvim-lspconfig

```lua
local lspconfig = require 'lspconfig'
local configs = require 'lspconfig.configs'

if not configs.systemd_ls then
  configs.systemd_ls = {
    default_config = {
      cmd = { 'systemd-language-server' },
      filetypes = { 'systemd' },
      root_dir = function() return nil end,
      single_file_support = true,
      settings = {},
    },
    docs = {
      description = [[
https://github.com/psacawa/systemd-language-server

Language Server for Systemd unit files.
]]
    }
  }
end

lspconfig.systemd_ls.setup {}
```

Courtesy of @ValdezFOmar

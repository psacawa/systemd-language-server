import logging
import os.path
import re
import sys
from argparse import ArgumentParser
from pathlib import Path

from lsprotocol.types import (
    INITIALIZE,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_HOVER,
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    CompletionOptions,
    CompletionParams,
    Hover,
    HoverParams,
    InitializedParams,
    Position,
    Range,
)
from pygls.server import LanguageServer
from pygls.workspace import TextDocument

from .unit import (
    UnitFileSection,
    UnitType,
    get_current_section,
    get_directives,
    get_documentation_content,
    get_unit_type,
    unit_type_to_unit_file_section,
)


class SystemdLanguageServer(LanguageServer):
    has_pandoc: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.has_pandoc = os.path.exists("/bin/pandoc")


server = SystemdLanguageServer("systemd-language-server", "v0.1")


@server.feature(INITIALIZE)
def initialize(params: InitializedParams):
    pass


def complete_unit_file_section(params: CompletionParams, unit_type: UnitType):
    possible_sections = [UnitFileSection.install, UnitFileSection.unit]
    section = unit_type_to_unit_file_section(unit_type)
    if section is not None:
        possible_sections.append(section)
    items = [
        CompletionItem(
            label=sec.value, insert_text=sec.value + "]", kind=CompletionItemKind.Struct
        )
        for sec in possible_sections
    ]
    return CompletionList(is_incomplete=False, items=items)


def complete_directive_property(
    params: CompletionParams,
    unit_type: UnitType,
    section: UnitFileSection | None,
    current_line: str,
):
    directive = current_line.split("=")[0]
    pass


def complete_directive(
    params: CompletionParams,
    unit_type: UnitType,
    section: UnitFileSection | None,
    current_line: str,
):
    directives = get_directives(unit_type, section)
    items = [
        CompletionItem(label=s, insert_text=s + "=", kind=CompletionItemKind.Property)
        for s in directives
        if s.startswith(current_line)
    ]
    return CompletionList(is_incomplete=False, items=items)


@server.feature(
    TEXT_DOCUMENT_COMPLETION, CompletionOptions(trigger_characters=["[', '="])
)
def textDocument_completion(params: CompletionParams) -> CompletionList | None:
    """Complete systemd unit properties. Determine the required completion type and
    dispatch it."""
    items = []
    uri = params.text_document.uri
    document = server.workspace.get_document(uri)
    current_line = document.lines[params.position.line].strip()
    unit_type = get_unit_type(document)
    section = get_current_section(document, params.position)

    if current_line == "[":
        return complete_unit_file_section(params, unit_type)
    elif "=" not in current_line:
        return complete_directive(params, unit_type, section, current_line)
    elif len(current_line.split("=")) == 2:
        return complete_directive_property(params, unit_type, section, current_line)


def range_for_directive(document: TextDocument, position: Position) -> Range:
    """Range indicating directive (before =)"""
    current_line = document.lines[position.line].strip()
    idx = current_line.find("=")
    return Range(Position(position.line, 0), Position(position.line, idx - 1))


@server.feature(TEXT_DOCUMENT_HOVER)
def textDocument_hover(params: HoverParams):
    """Help for unit file directives."""
    document = server.workspace.get_document(params.text_document.uri)
    current_line = document.lines[params.position.line].strip()
    unit_type = get_unit_type(document)
    section = get_current_section(document, params.position)

    if "=" in current_line:
        directive = current_line.split("=")[0]
        hover_range = range_for_directive(document, params.position)
        contents = get_documentation_content(
            directive, unit_type, section, server.has_pandoc
        )
        if contents is None:
            return None
        return Hover(contents=contents, range=hover_range)


def get_parser():
    parser = ArgumentParser()
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args(sys.argv[1:])
    server.start_io()

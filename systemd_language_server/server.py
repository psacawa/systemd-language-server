import re
import sys
from argparse import ArgumentParser
from pathlib import Path
import logging

from pygls.server import LanguageServer
from lsprotocol.types import (
    INITIALIZE,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_HOVER,
    CompletionParams,
    CompletionList,
    CompletionItem,
    CompletionItemKind,
    CompletionOptions,
    HoverParams,
    InitializedParams,
)
from .unit import (
    get_current_section,
    get_directives,
    UnitType,
    UnitFileSection,
    unit_type_to_unit_file_section,
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="systemd_language_server.log")
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
server = LanguageServer("systemd-language-server", "v0.1")

logging.basicConfig(
    filename="systemd_language_server.log", filemode="w", level=logging.DEBUG
)


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


def complete_directive_property(params: CompletionParams):
    #  TODO 10/02/20 psacawa: finish this
    pass


def complete_directive(
    params: CompletionParams,
    unit_type: UnitType,
    section: UnitFileSection | None,
    current_line: str,
):
    directives = get_directives(unit_type, section)
    logger.debug(directives)
    items = [
        CompletionItem(label=s, insert_text=s + "=", kind=CompletionItemKind.Property)
        for s in directives
        if s.startswith(current_line)
    ]
    return CompletionList(is_incomplete=False, items=items)


@server.feature(
    TEXT_DOCUMENT_COMPLETION, CompletionOptions(trigger_characters=["[', '="])
)
def text_document_completion(params: CompletionParams) -> CompletionList | None:
    """Complete systemd unit properties. Determine the required completion type and
    dispatch it."""
    items = []
    uri = params.text_document.uri
    document = server.workspace.get_document(uri)
    current_line = document.lines[params.position.line].strip()
    unit_type = UnitType(Path(uri).suffix.strip("."))
    section = get_current_section(document, params.position)
    logger.debug(f"{unit_type=} {section=}")

    if current_line == "[":
        return complete_unit_file_section(params, unit_type)
    elif "=" not in current_line:
        return complete_directive(params, unit_type, section, current_line)
    else:
        return None


@server.feature(TEXT_DOCUMENT_HOVER)
def text_document_hover(params: HoverParams):
    """Help for directives."""
    document = server.workspace.get_document(params.text_document.uri)
    current_line = document.lines[params.position.line].strip()


def get_parser():
    parser = ArgumentParser()
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args(sys.argv[1:])
    server.start_io()

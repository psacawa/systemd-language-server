import re
import sys
from argparse import ArgumentParser
from pathlib import Path
import logging

from pygls.server import LanguageServer
from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_HOVER,
    CompletionParams,
    CompletionList,
    CompletionItem,
    CompletionItemKind,
    HoverParams,
)
from .unit import get_current_section, get_directives, UnitType, UnitFileSection


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="systemd_language_server.log")
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)
server = LanguageServer("systemd-language-server", "v0.1")

logging.basicConfig(
    filename="systemd_language_server.log", filemode="w", level=logging.DEBUG
)


@server.feature(TEXT_DOCUMENT_COMPLETION)
def text_document_completion(params: CompletionParams) -> CompletionList:
    """Complete systemd unit properties."""
    items = []
    uri = params.text_document.uri
    document = server.workspace.get_document(uri)
    current_line = document.lines[params.position.line].strip()
    unit_type = UnitType(Path(uri).suffix.strip("."))

    #  section = UnitFileSection.unit
    section = get_current_section(document, params.position)
    logger.debug(f"{section=}")

    if not "=" in current_line:
        directives = get_directives(unit_type, section)
        logger.debug(directives)
        items = [
            CompletionItem(
                label=s, insert_text=s + "=", kind=CompletionItemKind.Property
            )
            for s in directives
            if s.startswith(current_line)
        ]

    return CompletionList(is_incomplete=False, items=items)


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

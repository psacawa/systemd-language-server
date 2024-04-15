import re
from concurrent.futures import TimeoutError
from dataclasses import dataclass
from pathlib import Path

import pytest
from lsprotocol.types import (
    INITIALIZE,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_HOVER,
    ClientCapabilities,
    CompletionList,
    CompletionParams,
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
    Hover,
    HoverParams,
    InitializeParams,
    MarkupContent,
    MarkupKind,
    Position,
    TextDocumentContentChangeEvent_Type2,
    TextDocumentIdentifier,
    TextDocumentItem,
    VersionedTextDocumentIdentifier,
)
from pygls.server import LanguageServer

from systemd_language_server.server import SystemdLanguageServer

ClientServerPair = tuple[LanguageServer, SystemdLanguageServer]

MAX_SERVER_INIT_RETRIES = 5


def client_init(client: LanguageServer, datadir: Path):
    for _ in range(MAX_SERVER_INIT_RETRIES):
        try:
            client.lsp.send_request(
                INITIALIZE,
                InitializeParams(
                    process_id=123,
                    root_uri=datadir.as_uri(),
                    capabilities=ClientCapabilities(),
                ),
            ).result(timeout=1)
        except TimeoutError:
            pass
        except:
            break


def client_open(client: LanguageServer, path: Path, text: str | None = None):
    if text is None:
        text = path.read_text()
    client.lsp.notify(
        TEXT_DOCUMENT_DID_OPEN,
        DidOpenTextDocumentParams(
            TextDocumentItem(
                text=text, uri=path.as_uri(), language_id="systemd", version=1
            ),
        ),
    )


@dataclass
class CompletionTestParams:
    filename: str | None
    text: str
    position: tuple[int, int]
    contains_completion_labels: list[str]
    excludes_completion_labels: list[str]


#  WorkingDirectory - systmed.exec.xml
#  ExecStart - systmed.service.xml
#  KillMode - systmed.kill.xml

no_section_test = CompletionTestParams(
    "test.service",
    "\n\n",
    (1, 0),
    ["Description", "ExecStart", "WorkingDirectory", "WantedBy", "KillMode"],
    [],
)
unit_section_test = CompletionTestParams(
    "test.service",
    "[Unit]\n\n",
    (1, 0),
    ["Description"],
    ["ExecStart", "WorkingDirectory", "WantedBy", "KillMode"],
)
install_section_test = CompletionTestParams(
    "test.service",
    "[Install]\n\n",
    (1, 0),
    ["WantedBy"],
    ["Description", "WorkingDirectory", "ExecStart", "KillMode"],
)
service_section_test = CompletionTestParams(
    "test.service",
    "[Service]\n\n",
    (1, 0),
    ["ExecStart", "WorkingDirectory", "KillMode"],
    ["Description", "WantedBy"],
)
socket_section_test = CompletionTestParams(
    "test.socket",
    "[Socket]\n\n",
    (1, 0),
    ["ListenStream", "WorkingDirectory", "KillMode"],
    ["ExecStart", "Description", "WantedBy"],
)
mount_section_test = CompletionTestParams(
    "test.mount",
    "[Mount]\n\n",
    (1, 0),
    ["What", "Where", "WorkingDirectory", "KillMode"],
    ["ExecStart", "Description", "WantedBy"],
)
timer_section_test = CompletionTestParams(
    "test.timer",
    "[Timer]\n\n",
    (1, 0),
    ["OnCalendar"],
    ["ExecStart", "Description", "WantedBy"],
)

#  completing "Exec"... in [Service] works as intended
service_directive_test = CompletionTestParams(
    "test.service",
    "[Service]\nExec\n",
    (1, 4),
    ["ExecStart", "ExecStartPre", "ExecStartPost"],
    ["WorkingDirectory", "KillMode"],
)


@pytest.mark.parametrize(
    "params",
    [
        no_section_test,
        unit_section_test,
        install_section_test,
        service_section_test,
        socket_section_test,
        mount_section_test,
        timer_section_test,
        service_directive_test,
    ],
)
def test_completion(client_server_pair: ClientServerPair, params: CompletionTestParams):
    client, server = client_server_pair

    datadir = Path(__file__).parent / "data"
    assert params.filename is not None
    unit_file = datadir / params.filename
    uri = unit_file.as_uri()

    client_init(client, datadir)
    client_open(client, unit_file)

    client.lsp.notify(
        TEXT_DOCUMENT_DID_CHANGE,
        params=DidChangeTextDocumentParams(
            text_document=VersionedTextDocumentIdentifier(version=1, uri=uri),
            content_changes=[TextDocumentContentChangeEvent_Type2(text=params.text)],
        ),
    )

    completion_list: CompletionList = client.lsp.send_request(
        TEXT_DOCUMENT_COMPLETION,
        params=CompletionParams(
            text_document=TextDocumentIdentifier(uri=uri),
            position=Position(*params.position),
            context=None,
        ),
    ).result(timeout=1)
    assert isinstance(completion_list, CompletionList)
    labels = [i.label for i in completion_list.items]
    for contained_label in params.contains_completion_labels:
        assert contained_label in labels
    for excluded_label in params.excludes_completion_labels:
        assert not excluded_label in labels


@dataclass
class HoverTestParams:
    filename: str | None
    text: str
    position: tuple[int, int]
    has_pandoc: bool
    pattern_returned: str | None


execstart_hover_markdown_test = HoverTestParams(
    "test.service",
    "[Service]\nExecStart=\n\n",
    (1, 0),
    True,
    r"Unless `Type=` is `oneshot`",  # from systemd.service.xml,
)
unit_hover_test = HoverTestParams(
    "test.service",
    "[Unit]\nDescription=\n\n",
    (1, 0),
    False,
    r"A short human readable title",  # from systemd.unit.xml,
)
service_hover_test = HoverTestParams(
    "test.service",
    "[Service]\nExecStart=\n\n",
    (1, 0),
    False,
    r"Commands that are executed when this service is started.",  # from systemd.service.xml,
)
kill_hover_test = HoverTestParams(
    "test.service",
    "[Service]\nKillMode=\n\n",
    (1, 0),
    False,
    r"Specifies how processes",  # from systemd.kill.xml,
)
install_hover_test = HoverTestParams(
    "test.service",
    "[Install]\nWantedBy=\n\n",
    (1, 0),
    False,
    r"This option may be used more than once,",  # from systemd.unit.xml,
)

fake_directive_hover_test = HoverTestParams(
    "test.service", "[Install]\nFakeDirective=\n\n", (1, 0), False, None
)
wrong_section_hover_test = HoverTestParams(
    "test.service", "[Install]\nExecStart=\n\n", (1, 0), False, None
)


@pytest.mark.parametrize(
    "params",
    [
        execstart_hover_markdown_test,
        unit_hover_test,
        service_hover_test,
        kill_hover_test,
        install_hover_test,
        fake_directive_hover_test,
        wrong_section_hover_test,
    ],
)
def test_hover(client_server_pair: ClientServerPair, params: HoverTestParams):
    client, server = client_server_pair
    server.has_pandoc = params.has_pandoc

    datadir = Path(__file__).parent / "data"
    assert params.filename is not None
    unit_file = datadir / params.filename
    uri = unit_file.as_uri()

    client_init(client, datadir)
    client_open(client, unit_file)

    client.lsp.notify(
        TEXT_DOCUMENT_DID_CHANGE,
        params=DidChangeTextDocumentParams(
            text_document=VersionedTextDocumentIdentifier(version=1, uri=uri),
            content_changes=[TextDocumentContentChangeEvent_Type2(text=params.text)],
        ),
    )

    hover: Hover = client.lsp.send_request(
        TEXT_DOCUMENT_HOVER,
        params=HoverParams(
            text_document=TextDocumentIdentifier(uri=uri),
            position=Position(*params.position),
        ),
    ).result(timeout=1)

    if params.pattern_returned is None:
        assert hover is None
        return

    assert isinstance(hover, Hover)

    content = hover.contents
    assert isinstance(content, MarkupContent)
    assert (content.kind == MarkupKind.Markdown) == params.has_pandoc
    assert re.search(params.pattern_returned, content.value) is not None

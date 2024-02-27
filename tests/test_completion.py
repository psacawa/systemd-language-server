from concurrent.futures import TimeoutError
from pathlib import Path

from lsprotocol.types import (
    INITIALIZE,
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
    ClientCapabilities,
    CompletionList,
    CompletionParams,
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
    InitializeParams,
    Position,
    Range,
    TextDocumentContentChangeEvent,
    TextDocumentContentChangeEvent_Type2,
    TextDocumentIdentifier,
    TextDocumentItem,
    VersionedTextDocumentIdentifier,
)
from pygls.server import LanguageServer
from pygls.workspace import text_document

from systemd_language_server.server import SystemdLanguageServer

ClientServerPair = tuple[LanguageServer, SystemdLanguageServer]

MAX_SERVER_INIT_RETRIES = 5


def client_init(client: LanguageServer, datadir: Path):
    print(__name__)
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


def test_basic(client_server_pair: ClientServerPair):
    client, server = client_server_pair
    print(client)
    print(server)

    datadir = Path(__file__).parent / "data"
    service_unit_file = datadir / "test.service"
    uri = service_unit_file.as_uri()

    client_init(client, datadir)
    client_open(client, service_unit_file)
    completion_list: CompletionList = client.lsp.send_request(
        TEXT_DOCUMENT_COMPLETION,
        params=CompletionParams(
            text_document=TextDocumentIdentifier(uri=uri),
            position=Position(1, 0),
            context=None,
        ),
    ).result(timeout=1)
    assert isinstance(completion_list, CompletionList)
    labels = [i.label for i in completion_list.items]
    assert "Description" in labels
    assert "ExecStart" not in labels

    client.lsp.notify(
        TEXT_DOCUMENT_DID_CHANGE,
        params=DidChangeTextDocumentParams(
            text_document=VersionedTextDocumentIdentifier(version=1, uri=uri),
            content_changes=[
                TextDocumentContentChangeEvent_Type2(text="[Service]\n\n")
            ],
        ),
    )

    completion_list = client.lsp.send_request(
        TEXT_DOCUMENT_COMPLETION,
        params=CompletionParams(
            text_document=TextDocumentIdentifier(uri=uri),
            position=Position(1, 0),
            context=None,
        ),
    ).result(timeout=1)
    assert isinstance(completion_list, CompletionList)
    labels = [i.label for i in completion_list.items]
    assert "Description" not in labels
    assert "ExecStart" in labels

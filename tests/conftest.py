import os
from threading import Thread
from typing import Iterable

import pytest
from lsprotocol.types import EXIT, SHUTDOWN
from pygls.server import LanguageServer

from systemd_language_server.server import SystemdLanguageServer


@pytest.fixture()
def client_server_pair() -> Iterable[tuple[LanguageServer, SystemdLanguageServer]]:
    """
    Fixture to create a client and server in their own threads communicating over a pair
    of pipes. Inspired by pygls.tests.  client_server
    """
    r_cs, w_cs = os.pipe()
    r_sc, w_sc = os.pipe()

    thread_main = lambda client_or_server, read, write: client_or_server.start_io(
        os.fdopen(read, "rb"), os.fdopen(write, "wb")
    )
    client = LanguageServer("client", "v1")
    client_thread = Thread(target=thread_main, args=[client, r_sc, w_cs])
    client_thread.start()

    server = SystemdLanguageServer("systemd-server", "v0")
    server_thread = Thread(target=thread_main, args=[server, r_cs, w_sc])
    server_thread.start()

    #  pytest stupid solution for fixture teardown is python genertors: the first yielded
    #  value is the fixture, then the fixture is deconstructed
    yield client, server

    client.lsp.send_request(SHUTDOWN)
    client.lsp.notify(EXIT)
    client_thread.join()
    server_thread.join()

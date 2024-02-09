import re
from enum import Enum, auto
from itertools import islice
import logging

from pygls.workspace import TextDocument
from lsprotocol.types import Position

SECTION_HEADER_PROG = re.compile(r"^\[(?P<name>\w+)\]$")

from .constants import (
    systemd_unit_directives,
    systemd_install_directives,
    systemd_service_directives,
    systemd_socket_directives,
    systemd_mount_directives,
    systemd_automount_directives,
    systemd_timer_directives,
    systemd_scope_directives,
    systemd_swap_directives,
    systemd_path_directives,
    systemd_exec_directives,
    systemd_kill_directives,
)


class UnitType(Enum):
    service = "service"
    socket = "socket"
    device = "device"
    mount = "mount"
    automount = "automount"
    swap = "swap"
    target = "target"
    path = "path"
    timer = "timer"
    slice = "slice"
    scope = "scope"


class UnitFileSection(Enum):
    unit = "unit"
    install = "install"
    service = "service"
    socket = "socket"
    mount = "mount"
    automount = "automount"
    swap = "swap"
    path = "path"
    timer = "timer"


directive_dict = {
    UnitFileSection.service: systemd_service_directives,
    UnitFileSection.timer: systemd_timer_directives,
    UnitFileSection.socket: systemd_socket_directives,
    UnitFileSection.mount: systemd_mount_directives,
    UnitFileSection.automount: systemd_automount_directives,
    UnitFileSection.swap: systemd_swap_directives,
    UnitFileSection.path: systemd_path_directives,
}


def get_directives(unit_type: UnitType, section: UnitFileSection | None) -> list[str]:
    if section is None:
        return []
    if section == UnitFileSection.unit:
        return systemd_unit_directives
    if section == UnitFileSection.install:
        return systemd_install_directives
    directives = directive_dict[section]
    if unit_type in [
        UnitType.service,
        UnitType.socket,
        UnitType.mount,
        UnitType.swap,
    ]:
        directives += systemd_exec_directives + systemd_kill_directives
    return directives

    return []


def get_current_section(
    document: TextDocument, position: Position
) -> UnitFileSection | None:
    """Determine section of cursor in current document"""

    for i in reversed(range(0, position.line)):
        line = document.lines[i].strip()
        match = SECTION_HEADER_PROG.search(line)
        logging.debug(f"{line=} {match=}")
        if match is not None:
            try:
                section = UnitFileSection(match.group("name").lower())
                return section
            except ValueError:
                pass
    return None

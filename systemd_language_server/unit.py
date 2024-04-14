import re
import subprocess
from enum import Enum
from glob import glob
from io import StringIO
from pathlib import Path

from lsprotocol.types import MarkupContent, MarkupKind, Position
from lxml import etree  # type: ignore
from pygls.workspace import TextDocument

from .constants import (
    systemd_automount_directives,
    systemd_exec_directives,
    systemd_install_directives,
    systemd_kill_directives,
    systemd_mount_directives,
    systemd_path_directives,
    systemd_scope_directives,
    systemd_service_directives,
    systemd_socket_directives,
    systemd_swap_directives,
    systemd_timer_directives,
    systemd_unit_directives,
)

#  The ultimate source for information on unit files is the docbook files distributed with
#  systemd. Therefore, the following data is managed by the language server:
#  - unit type
#  - unit file sections
#  - directives
#  - directive values
#  - which docbook (.xml) directives are documented in
#  Data is resolved at runtime, to the extent possible, therefore docbooks are bundled
#  with systemd-language-server and parsed as required.

SECTION_HEADER_PROG = re.compile(r"^\[(?P<name>\w+)\]$")


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

    def is_execable(self):
        return self in [
            UnitType.service,
            UnitType.socket,
            UnitType.mount,
            UnitType.swap,
        ]


class UnitFileSection(Enum):
    unit = "Unit"
    install = "Install"
    service = "Service"
    socket = "Socket"
    mount = "Mount"
    automount = "Automount"
    scope = "Scope"
    swap = "Swap"
    path = "Path"
    timer = "Timer"


_assets_dir = Path(__file__).absolute().parent / "assets"
docbooks = glob("*.xml", root_dir=_assets_dir)

#  dict mapping docbook documentation file to the list of  systemd unit directives
#  documented within
directives = dict()


def initialize_directive():
    for filename in docbooks:
        docbook_file = _assets_dir / filename
        tree = etree.parse(open(docbook_file).read())
        directives[filename] = tree.xpath()
        #  TODO 10/02/20 psacawa: finish this


def unit_type_to_unit_file_section(ut: UnitType) -> UnitFileSection | None:
    try:
        return UnitFileSection(ut.value.capitalize())
    except Exception:
        return None


def unit_file_section_to_unit_type(ufs: UnitFileSection) -> UnitType | None:
    try:
        return UnitType(ufs.value.lower())
    except Exception:
        return None


directive_dict = {
    UnitFileSection.service: systemd_service_directives,
    UnitFileSection.timer: systemd_timer_directives,
    UnitFileSection.socket: systemd_socket_directives,
    UnitFileSection.mount: systemd_mount_directives,
    UnitFileSection.automount: systemd_automount_directives,
    UnitFileSection.swap: systemd_swap_directives,
    UnitFileSection.path: systemd_path_directives,
    UnitFileSection.scope: systemd_scope_directives,
}


def convert_to_markdown(raw_varlistentry: bytes):
    """Use pandoc to convert docbook entry to markdown"""
    argv = "pandoc --from=docbook --to markdown -".split()
    proc = subprocess.run(argv, input=raw_varlistentry, stdout=subprocess.PIPE)
    return proc.stdout.decode()


def get_documentation_content(
    directive: str,
    unit_type: UnitType,
    section: UnitFileSection | None,
    markdown_available=False,
) -> MarkupContent | None:
    """Get documentation for unit file directive."""
    docbooks = get_manual_sections(unit_type, section)
    for manual in docbooks:
        filepath = _assets_dir / manual
        stream = StringIO(open(filepath).read())
        tree = etree.parse(stream)
        for varlistentry in tree.xpath("//varlistentry"):
            directives_in_varlist: list[str] = [
                varname.text.strip("=")
                for varname in varlistentry.findall(".//term/varname")
            ]
            if directive not in directives_in_varlist:
                continue
            raw_varlistentry = etree.tostring(varlistentry)
            value = bytes()
            kind: MarkupKind
            if markdown_available:
                kind = MarkupKind.Markdown
                value = convert_to_markdown(raw_varlistentry)
            else:
                kind = MarkupKind.PlainText
                value = "".join((varlistentry.itertext()))

            return MarkupContent(kind=kind, value=value)
    return None


def get_manual_sections(unit_type: UnitType, section: UnitFileSection | None):
    """Determine which docbook to search for documentation, based on unit type and file
    section. If no section is provided, search liberally, search liberally."""
    if section in [UnitFileSection.unit, UnitFileSection.install]:
        return ["systemd.unit.xml"]
    ret = ["systemd.{}.xml".format(unit_type.value.lower())]
    if section is None:
        ret += ["systemd.unit.xml", "systemd.install.xml"]
    if unit_type.is_execable():
        ret += ["systemd.exec.xml", "systemd.kill.xml"]
    return ret


def get_directives(unit_type: UnitType, section: UnitFileSection | None) -> list[str]:
    #  Two variants: i) the current unit file section is known, ii) it isn't (e.g. buffer
    #  has no section headers yet). If it is, we supply completions value for the unit
    #  type/section. Otherwise, we supply those valid for all sections.
    if section == UnitFileSection.unit:
        return systemd_unit_directives
    if section == UnitFileSection.install:
        return systemd_install_directives

    directives: list[str] = []
    if section is None:
        #  if unit type has a corresponding unit file section, add it
        section_from_type = unit_type_to_unit_file_section(unit_type)
        if section_from_type is not None:
            directives += directive_dict[section_from_type]
        directives += systemd_unit_directives + systemd_install_directives
    else:
        directives = directive_dict[section]

    if unit_type.is_execable():
        directives += systemd_exec_directives + systemd_kill_directives
    return directives


def get_unit_type(document):
    return UnitType(Path(document.uri).suffix.strip("."))


def get_current_section(
    document: TextDocument, position: Position
) -> UnitFileSection | None:
    """Determine section of cursor in current document"""

    for i in reversed(range(0, position.line)):
        line = document.lines[i].strip()
        match = SECTION_HEADER_PROG.search(line)
        if match is not None:
            try:
                section = UnitFileSection(match.group("name"))
                return section
            except ValueError:
                pass
    return None

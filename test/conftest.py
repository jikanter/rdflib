from __future__ import annotations

import sys
from contextlib import ExitStack

import pytest

# This is here so that asserts from these modules are formatted for human
# readability.
pytest.register_assert_rewrite("test.utils")

from collections.abc import Collection, Generator, Iterable
from pathlib import Path

from rdflib import Graph
from test.utils.audit import AuditHookDispatcher
from test.utils.http import ctx_http_server
from test.utils.httpfileserver import HTTPFileServer

from .data import TEST_DATA_DIR
from .utils.earl import EARLReporter
from .utils.httpservermock import ServedBaseHTTPServerMock

# This try/catch block allows this library to be used
# as a submodule to a larger project
# pytest_plugins = None
# try:
#     pytest_plugins
# except NameError as e:
#     pytest_plugins = [EARLReporter.__module__]


@pytest.fixture(scope="session")
def http_file_server() -> Generator[HTTPFileServer, None, None]:
    host = "127.0.0.1"
    server = HTTPFileServer((host, 0))
    with ctx_http_server(server) as served:
        yield served


@pytest.fixture(scope="session")
def rdfs_graph() -> Graph:
    return Graph().parse(TEST_DATA_DIR / "defined_namespaces/rdfs.ttl", format="turtle")


_ServedBaseHTTPServerMocks = tuple[ServedBaseHTTPServerMock, ServedBaseHTTPServerMock]


@pytest.fixture(scope="session")
def _session_function_httpmocks() -> Generator[_ServedBaseHTTPServerMocks, None, None]:
    """
    This fixture is session scoped, but it is reset for each function in
    :func:`function_httpmock`. This should not be used directly.
    """
    with (
        ServedBaseHTTPServerMock() as httpmock_a,
        ServedBaseHTTPServerMock() as httpmock_b,
    ):
        yield httpmock_a, httpmock_b


@pytest.fixture(scope="function")
def function_httpmock(
    _session_function_httpmocks: _ServedBaseHTTPServerMocks,
) -> Generator[ServedBaseHTTPServerMock, None, None]:
    """
    HTTP server mock that is reset for each test function.
    """
    (mock, _) = _session_function_httpmocks
    mock.reset()
    yield mock


@pytest.fixture(scope="function")
def function_httpmocks(
    _session_function_httpmocks: _ServedBaseHTTPServerMocks,
) -> Generator[tuple[ServedBaseHTTPServerMock, ServedBaseHTTPServerMock], None, None]:
    """
    Alternative HTTP server mock that is reset for each test function.

    This exists in case a tests needs to work with two different HTTP servers.
    """
    (mock_a, mock_b) = _session_function_httpmocks
    mock_a.reset()
    mock_b.reset()
    yield mock_a, mock_b


@pytest.fixture(scope="session", autouse=True)
def audit_hook_dispatcher() -> Generator[AuditHookDispatcher, None, None]:
    dispatcher = AuditHookDispatcher()
    sys.addaudithook(dispatcher.audit)
    yield dispatcher


@pytest.fixture(scope="function")
def exit_stack() -> Generator[ExitStack, None, None]:
    with ExitStack() as stack:
        yield stack


EXTRA_MARKERS: dict[tuple[str | None, str], Collection[pytest.MarkDecorator | str]] = {
    ("rdflib/__init__.py", "rdflib"): [pytest.mark.webtest],
    ("rdflib/term.py", "rdflib.term.Literal.normalize"): [pytest.mark.webtest],
    ("rdflib/extras/infixowl.py", "rdflib.extras.infixowl"): [pytest.mark.webtest],
}


PROJECT_ROOT = Path(__file__).parent.parent


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: Iterable[pytest.Item]):
    for item in items:
        if config and not config.getoption("--public-endpoints", False):
            # Skip tests marked with public_endpoints if the option is not provided
            if "public_endpoints" in item.keywords:
                item.add_marker(
                    pytest.mark.skip(reason="need --public-endpoints option to run")
                )

        parent_name = (
            str(Path(item.parent.module.__file__).relative_to(PROJECT_ROOT))
            if item.parent is not None
            and isinstance(item.parent, pytest.Module)
            and item.parent.module is not None
            else None
        )
        if (parent_name, item.name) in EXTRA_MARKERS:
            extra_markers = EXTRA_MARKERS[(parent_name, item.name)]
            for extra_marker in extra_markers:
                item.add_marker(extra_marker)


def pytest_addoption(parser):
    """Add optional pytest markers to run tests on public endpoints"""
    parser.addoption(
        "--public-endpoints",
        action="store_true",
        default=False,
        help="run tests that require public SPARQL endpoints",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "public_endpoints: mark tests that require public SPARQL endpoints"
    )

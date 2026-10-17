"""Current libtmux's actual parser and private-socket tmux lifecycle."""
import shutil
import subprocess
import threading
import time

import libtmux
import pytest
from libtmux import neo
from cli_agent_orchestrator.clients.tmux import TmuxClient, TmuxLookupError


@pytest.mark.parametrize('command', ['list-sessions', 'list-windows', 'list-panes'])
def test_scope_aware_parser_retains_empty_values_and_rejects_malformed_rows(command):
    fields, _ = neo.get_output_format(command, '3.8')
    assert 'server' not in fields and 'client_name' not in fields
    assert {'session_id', 'window_id', 'pane_id'} <= set(fields)
    values = [''] * len(fields)
    for key, value in [('session_id', '$1'), ('window_id', '@2'), ('pane_id', '%3')]:
        values[fields.index(key)] = value
    row = neo.FORMAT_SEPARATOR.join(values)+neo.FORMAT_SEPARATOR
    parsed = TmuxClient._read_listing(command, lambda: neo.parse_output(row, command, '3.8'))
    assert parsed == {'session_id': '$1', 'window_id': '@2', 'pane_id': '%3'}
    short = neo.FORMAT_SEPARATOR.join(values[:-1])+neo.FORMAT_SEPARATOR
    with pytest.raises(TmuxLookupError):
        TmuxClient._read_listing(command, lambda: neo.parse_output(short, command, '3.8'))


@pytest.mark.skipif(not shutil.which('tmux'), reason='real tmux executable required')
def test_private_socket_anchor_survives_concurrent_session_disappearance(tmp_path):
    sock = tmp_path/'tmux.sock'
    server = libtmux.Server(socket_path=str(sock))
    client = TmuxClient(); client.server = server
    failures = []; stopping = threading.Event()
    def churn():
        try:
            for index in range(20):
                if stopping.is_set(): break
                name = f'vanishing-{index}'
                subprocess.run(['tmux', '-S', str(sock), 'new-session', '-d', '-s', name],
                               check=True, capture_output=True, timeout=3)
                subprocess.run(['tmux', '-S', str(sock), 'kill-session', '-t', name],
                               check=True, capture_output=True, timeout=3)
        except Exception as exc: failures.append(exc)
    thread = threading.Thread(target=churn)
    try:
        client.create_session('anchor', 'main', 'fixture', str(tmp_path))
        thread.start(); reads = 0; unknown = 0; cutoff = time.monotonic()+15
        while (thread.is_alive() or reads < 10) and time.monotonic() < cutoff:
            try:
                names = client.list_sessions()
                assert 'anchor' in {row['name'] for row in names}
                assert client.session_exists_strict('anchor') is True
                client.get_history('anchor', 'main')
                reads += 1
            except TmuxLookupError:
                # An unreadable row is unknown, never an absent anchor.
                unknown += 1
        assert reads >= 10 and not failures, (reads, unknown, failures)
    finally:
        stopping.set()
        if thread.ident: thread.join(timeout=5)
        subprocess.run(['tmux', '-S', str(sock), 'kill-server'], capture_output=True, timeout=5)
    assert not thread.is_alive()

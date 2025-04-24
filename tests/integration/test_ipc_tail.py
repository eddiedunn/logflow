import os
import socket
import threading
import time
import subprocess
import sys
import pytest
from contextlib import closing
import select

def get_free_udp_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def get_free_tcp_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

@pytest.mark.integration
@pytest.mark.timeout(30)
def test_ipc_tail():
    # Ensure no lingering logflow.listener processes
    print("[TEST] Killing any lingering logflow.listener processes...")
    try:
        subprocess.run(["pkill", "-f", "logflow.listener"], check=False)
        time.sleep(0.5)  # Give the OS a moment to reap
    except Exception as e:
        print(f"[TEST] pkill failed: {e}")

    sock_path = "/tmp/logflow-listener-test.sock"
    udp_port = get_free_udp_port()
    health_port = get_free_tcp_port()
    print(f"[TEST] Using UDP port {udp_port}, health port {health_port}")
    env = os.environ.copy()
    env["LOGFLOW_IPC_SOCKET"] = sock_path
    env["UDP_LOG_LISTEN_PORT"] = str(udp_port)
    env["UDP_BATCH_INTERVAL"] = "0.1"
    env["LOGFLOW_HEALTH_PORT"] = str(health_port)
    print("[TEST] Cleaning up socket if exists...")
    try:
        os.unlink(sock_path)
    except FileNotFoundError:
        pass
    print("[TEST] Starting primary listener...")
    primary = subprocess.Popen(
        [sys.executable, "-m", "logflow.listener"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    for i in range(50):
        if os.path.exists(sock_path):
            print(f"[TEST] IPC socket created after {i*0.1:.1f}s.")
            break
        if primary.poll() is not None:
            print("[TEST] Primary exited early:", primary.stdout.read())
            assert False, "Primary exited before IPC socket was created"
        time.sleep(0.1)
    else:
        primary.terminate()
        print("[TEST] Timeout waiting for IPC socket.")
        assert False, f"IPC socket {sock_path} was not created in time"
    print("[TEST] Starting tail client...")
    tail = subprocess.Popen(
        [sys.executable, "-m", "logflow.listener"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    time.sleep(1.0)
    print("[TEST] Sending UDP log message...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = b"test-ipc-tail-message"
    sock.sendto(msg, ("127.0.0.1", udp_port))

    print("[TEST] Waiting for output from both processes (non-blocking)...")
    found_primary = found_tail = False
    primary_out = ""
    tail_out = ""
    for j in range(50):
        # Non-blocking read using select
        for proc, name in [(primary, "primary"), (tail, "tail")]:
            if proc.stdout:
                rlist, _, _ = select.select([proc.stdout], [], [], 0)
                if rlist:
                    try:
                        chunk = os.read(proc.stdout.fileno(), 4096).decode(errors="replace")
                        if name == "primary":
                            primary_out += chunk
                        else:
                            tail_out += chunk
                    except Exception as e:
                        print(f"[TEST] Exception reading {name} stdout: {e}")
        if "test-ipc-tail-message" in primary_out:
            found_primary = True
        if "test-ipc-tail-message" in tail_out:
            found_tail = True
        if found_primary and found_tail:
            print(f"[TEST] Both outputs found after {j*0.1:.1f}s.")
            break
        time.sleep(0.1)
    print("[TEST] Terminating both processes...")
    primary.terminate()
    tail.terminate()
    try:
        primary.wait(timeout=3)
    except subprocess.TimeoutExpired:
        print("[TEST] Primary did not exit, killing...")
        primary.kill()
    try:
        tail.wait(timeout=3)
    except subprocess.TimeoutExpired:
        print("[TEST] Tail did not exit, killing...")
        tail.kill()
    print("[TEST] Collecting any remaining output with communicate...")
    try:
        p_remain, _ = primary.communicate(timeout=2)
        primary_out += p_remain
    except Exception as e:
        print(f"[TEST] Primary communicate failed: {e}")
    try:
        t_remain, _ = tail.communicate(timeout=2)
        tail_out += t_remain
    except Exception as e:
        print(f"[TEST] Tail communicate failed: {e}")
    print("PRIMARY OUT:\n", primary_out)
    print("TAIL OUT:\n", tail_out)
    assert "test-ipc-tail-message" in primary_out
    assert "test-ipc-tail-message" in tail_out
    assert "Tail client connected" in primary_out
    assert "Connected as tail client" in tail_out
    if "Tail client disconnected" not in primary_out:
        print("[TEST] WARNING: 'Tail client disconnected' not found in primary output.")
    print("[TEST] Cleaning up socket...")
    try:
        os.unlink(sock_path)
    except FileNotFoundError:
        pass
    print("[TEST] Test completed successfully.")

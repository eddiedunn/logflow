import os
import socket
import sys
import threading
import time
from contextlib import closing

# Default UNIX socket path for IPC between primary and tail listeners
LOGFLOW_IPC_SOCKET = os.getenv("LOGFLOW_IPC_SOCKET", "/tmp/logflow-listener.sock")

class IPCServer:
    def __init__(self, sock_path=LOGFLOW_IPC_SOCKET, max_clients=None):
        self.sock_path = sock_path
        if max_clients is None:
            self.max_clients = int(os.getenv("LOGFLOW_MAX_TAIL_CLIENTS", 5))
        else:
            self.max_clients = max_clients
        print(f"[IPCServer] Initialized with max_clients={self.max_clients}")
        sys.stdout.flush()
        self.clients = []  # List of connected sockets
        self.lock = threading.Lock()
        self.server_sock = None
        self.running = False
        self.accept_thread = None

    def start(self):
        if os.path.exists(self.sock_path):
            try:
                # Try to connect to see if it's stale
                with closing(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)) as s:
                    s.connect(self.sock_path)
                    # If connect succeeds, someone is running
                    raise RuntimeError(f"IPC socket already in use: {self.sock_path}")
            except (ConnectionRefusedError, FileNotFoundError):
                os.unlink(self.sock_path)
        self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_sock.bind(self.sock_path)
        self.server_sock.listen(self.max_clients)
        self.running = True
        self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.accept_thread.start()

    def _accept_loop(self):
        while self.running:
            try:
                client_sock, _ = self.server_sock.accept()
                with self.lock:
                    # ATOMIC: check before appending
                    print(f"[IPCServer] Accepting connection. Current clients: {len(self.clients)} / {self.max_clients}")
                    if len(self.clients) >= self.max_clients:
                        print("[IPCServer] Too many clients, rejecting new connection.")
                        client_sock.sendall(b"[logflow] Too many tail clients connected.\n")
                        try:
                            client_sock.shutdown(socket.SHUT_WR)
                        except Exception as e:
                            print(f"[IPCServer] Shutdown error: {e}")
                        time.sleep(0.2)
                        print("[IPCServer] Closing client socket after error...")
                        client_sock.close()
                        print("[IPCServer] Client socket closed after error.")
                        sys.stdout.flush()
                        continue
                    self.clients.append(client_sock)
                print(f"[logflow] Tail client connected. Total: {len(self.clients)}")
                sys.stdout.flush()
                threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"[logflow] IPC accept error: {e}")
                    sys.stdout.flush()

    def _handle_client(self, client_sock):
        try:
            while self.running:
                data = client_sock.recv(1)
                if not data:
                    break  # Client disconnected
        except Exception:
            pass
        finally:
            with self.lock:
                if client_sock in self.clients:
                    self.clients.remove(client_sock)
            client_sock.close()
            print(f"[logflow] Tail client disconnected. Total: {len(self.clients)}")

    def broadcast(self, line: str):
        with self.lock:
            for client in list(self.clients):
                try:
                    client.sendall(line.encode(errors="replace") + b"\n")
                except Exception:
                    self.clients.remove(client)
                    client.close()
                    print(f"[logflow] Tail client forcibly disconnected. Total: {len(self.clients)}")

    def stop(self):
        self.running = False
        if self.server_sock:
            self.server_sock.close()
        if os.path.exists(self.sock_path):
            try:
                os.unlink(self.sock_path)
            except Exception:
                pass
        with self.lock:
            for client in self.clients:
                try:
                    client.close()
                except Exception:
                    pass
            self.clients.clear()

class IPCClient:
    def __init__(self, sock_path=LOGFLOW_IPC_SOCKET):
        self.sock_path = sock_path
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def connect(self):
        print(f"[IPCClient] Connecting to {self.sock_path}")
        self.sock.connect(self.sock_path)
        print(f"[IPCClient] Connected!")

    def tail(self):
        try:
            while True:
                line = b""
                while not line.endswith(b"\n"):
                    chunk = self.sock.recv(1024)
                    if not chunk:
                        break
                    line += chunk
                if not line:
                    break
                print(line.decode(errors="replace"), end="")
            # After main loop, check if any partial data left
            try:
                leftover = self.sock.recv(1024)
                if leftover:
                    print("[IPCClient] Received data before close:", leftover.decode(errors="replace"))
            except Exception as e:
                print(f"[IPCClient] Exception on final recv: {e}")
        finally:
            try:
                self.sock.close()
            except Exception:
                pass
            print("[IPCClient] Socket closed")

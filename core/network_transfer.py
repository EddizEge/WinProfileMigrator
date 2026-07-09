"""
WinProfileMigrator - Ağ Transferi
İki bilgisayar arasında doğrudan ağ üzerinden profil aktarma.
"""
import os
import json
import socket
import struct
import logging
import threading
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("WinProfileMigrator.network")

# Protokol sabitleri
DISCOVERY_PORT = 52788
TRANSFER_PORT = 52789
BUFFER_SIZE = 65536
MAGIC_HEADER = b"WPMIG01"
DISCOVERY_MSG = b"WPMIG_DISCOVER"
DISCOVERY_RESP = b"WPMIG_HERE"


class SocketWriter:
    """Socket üzerinden dosya gibi yazmayı sağlayan yardımcı sınıf."""
    def __init__(self, sock, cancel_event, total_size=0, progress_cb=None):
        self.sock = sock
        self.cancel_event = cancel_event
        self.bytes_written = 0
        self.total_size = total_size
        self.progress_cb = progress_cb
        self.start_time = time.time()
        self.last_report_time = self.start_time

    def write(self, data):
        if self.cancel_event.is_set():
            raise IOError("Transfer iptal edildi")
        self.sock.sendall(data)
        self.bytes_written += len(data)
        
        if self.progress_cb:
            now = time.time()
            if now - self.last_report_time > 0.5:
                speed = (self.bytes_written / (1024 * 1024)) / max(now - self.start_time, 0.001)
                self.progress_cb(self.bytes_written, self.total_size, speed)
                self.last_report_time = now
                
        return len(data)

    def flush(self):
        pass

    def tell(self):
        return self.bytes_written

    def close(self):
        # We don't close the socket here because we need to read the OK response
        pass


class NetworkTransfer:
    """Ağ üzerinden profil transferi."""

    def __init__(self):
        self._running = False
        self._server_thread = None
        self._discovery_thread = None
        self._cancel_event = threading.Event()

    def stop(self):
        """Tüm işlemleri durdur."""
        self._running = False
        self._cancel_event.set()

    def discover_peers(self, timeout: float = 5.0,
                        callback: Optional[Callable] = None) -> list:
        """
        Yerel ağda WinProfileMigrator çalıştıran bilgisayarları keşfet.

        Args:
            timeout: Keşif süresi (saniye)
            callback: Bulunan cihaz callback(ip, hostname, info)

        Returns:
            Bulunan cihazların listesi
        """
        peers = []

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(1.0)

            # Broadcast gönder
            local_info = json.dumps({
                "hostname": socket.gethostname(),
                "username": os.environ.get("USERNAME", ""),
            }).encode("utf-8")

            broadcast_msg = DISCOVERY_MSG + b"|" + local_info
            sock.sendto(broadcast_msg, ("<broadcast>", DISCOVERY_PORT))

            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(4096)
                    if data.startswith(DISCOVERY_RESP):
                        info_data = data[len(DISCOVERY_RESP) + 1:]
                        try:
                            peer_info = json.loads(info_data.decode("utf-8"))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            peer_info = {}

                        peer = {
                            "ip": addr[0],
                            "port": TRANSFER_PORT,
                            "hostname": peer_info.get("hostname", "Bilinmiyor"),
                            "username": peer_info.get("username", ""),
                        }

                        # Kendimizi ekleme
                        if addr[0] != self._get_local_ip():
                            peers.append(peer)
                            if callback:
                                callback(peer["ip"], peer["hostname"], peer)

                except socket.timeout:
                    continue

            sock.close()

        except Exception as e:
            logger.error("Keşif hatası: %s", e)

        return peers

    def start_discovery_responder(self):
        """Keşif isteklerine yanıt veren dinleyiciyi başlat."""
        self._running = True
        self._discovery_thread = threading.Thread(
            target=self._discovery_responder_loop, daemon=True
        )
        self._discovery_thread.start()

    def _discovery_responder_loop(self):
        """Keşif yanıtlayıcı döngüsü."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)
            sock.bind(("", DISCOVERY_PORT))

            local_info = json.dumps({
                "hostname": socket.gethostname(),
                "username": os.environ.get("USERNAME", ""),
            }).encode("utf-8")

            while self._running:
                try:
                    data, addr = sock.recvfrom(4096)
                    if data.startswith(DISCOVERY_MSG):
                        response = DISCOVERY_RESP + b"|" + local_info
                        sock.sendto(response, addr)
                        logger.info("Keşif isteğine yanıt verildi: %s", addr[0])
                except socket.timeout:
                    continue

            sock.close()
        except Exception as e:
            logger.error("Keşif yanıtlayıcı hatası: %s", e)

    def send_file(self, file_path: Path, target_ip: str,
                   progress_callback: Optional[Callable] = None) -> bool:
        """
        Bir dosyayı ağ üzerinden gönder.

        Args:
            file_path: Gönderilecek dosya
            target_ip: Hedef IP adresi
            progress_callback: İlerleme callback(sent_bytes, total_bytes, speed_mbps)
        """
        self._cancel_event.clear()

        if not file_path.exists():
            logger.error("Dosya bulunamadı: %s", file_path)
            return False

        file_size = file_path.stat().st_size
        file_name = file_path.name

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((target_ip, TRANSFER_PORT))

            # Header gönder: magic + dosya adı uzunluğu + dosya adı + dosya boyutu
            name_bytes = file_name.encode("utf-8")
            header = MAGIC_HEADER + struct.pack("!I", len(name_bytes)) + name_bytes
            header += struct.pack("!Q", file_size)
            sock.sendall(header)

            # Dosyayı gönder
            sent = 0
            start_time = time.time()

            with open(file_path, "rb") as f:
                while sent < file_size:
                    if self._cancel_event.is_set():
                        logger.info("Transfer iptal edildi")
                        sock.close()
                        return False

                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        break

                    sock.sendall(chunk)
                    sent += len(chunk)

                    if progress_callback:
                        elapsed = time.time() - start_time
                        speed = (sent / (1024 * 1024)) / max(elapsed, 0.001)
                        progress_callback(sent, file_size, speed)

            # Onay bekle
            sock.settimeout(30)
            response = sock.recv(2)
            sock.close()

            if response == b"OK":
                logger.info("Dosya başarıyla gönderildi: %s", file_name)
                return True
            else:
                logger.error("Transfer onayı alınamadı")
                return False

        except Exception as e:
            logger.error("Gönderme hatası: %s", e)
            return False

    def open_stream_connection(self, target_ip: str, file_name: str, total_size: int = 0, progress_cb: Optional[Callable] = None):
        """
        Alıcıya stream (akış) moduyla bağlan.
        Dönen SocketWriter nesnesi doğrudan tarfile'a verilebilir.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((target_ip, TRANSFER_PORT))

            # Header gönder (size = 0xFFFFFFFFFFFFFFFF = stream mode)
            name_bytes = file_name.encode("utf-8")
            header = MAGIC_HEADER + struct.pack("!I", len(name_bytes)) + name_bytes
            header += struct.pack("!Q", 0xFFFFFFFFFFFFFFFF)
            sock.sendall(header)
            
            return sock, SocketWriter(sock, self._cancel_event, total_size, progress_cb)
        except Exception as e:
            logger.error("Bağlantı hatası: %s", e)
            return None, None

    def start_receiver(self, save_dir: Path,
                        progress_callback: Optional[Callable] = None,
                        complete_callback: Optional[Callable] = None):
        """
        Dosya alıcısını başlat (arka planda).

        Args:
            save_dir: Alınan dosyaların kaydedileceği dizin
            progress_callback: İlerleme callback(received, total, speed)
            complete_callback: Tamamlanma callback(file_path, success)
        """
        self._running = True
        self._cancel_event.clear()

        self._server_thread = threading.Thread(
            target=self._receiver_loop,
            args=(save_dir, progress_callback, complete_callback),
            daemon=True
        )
        self._server_thread.start()

    def _receiver_loop(self, save_dir: Path,
                        progress_callback, complete_callback):
        """Alıcı döngüsü."""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.settimeout(2.0)
            server.bind(("", TRANSFER_PORT))
            server.listen(1)

            logger.info("Alıcı başlatıldı, port: %d", TRANSFER_PORT)

            while self._running:
                try:
                    conn, addr = server.accept()
                    logger.info("Bağlantı alındı: %s", addr[0])

                    # Header oku
                    magic = conn.recv(len(MAGIC_HEADER))
                    if magic != MAGIC_HEADER:
                        logger.warning("Geçersiz magic header")
                        conn.close()
                        continue

                    # Dosya adı
                    name_len_data = conn.recv(4)
                    name_len = struct.unpack("!I", name_len_data)[0]
                    name_data = conn.recv(name_len)
                    file_name = name_data.decode("utf-8")

                    # Dosya boyutu
                    size_data = conn.recv(8)
                    file_size = struct.unpack("!Q", size_data)[0]

                    logger.info("Dosya alınıyor: %s (%d bytes)", file_name, file_size)

                    # Dosyayı al
                    save_dir.mkdir(parents=True, exist_ok=True)
                    save_path = save_dir / file_name
                    received = 0
                    start_time = time.time()

                    with open(save_path, "wb") as f:
                        is_stream = file_size == 0xFFFFFFFFFFFFFFFF
                        while True:
                            if self._cancel_event.is_set():
                                conn.close()
                                if save_path.exists():
                                    save_path.unlink()
                                return

                            if is_stream:
                                chunk_size = BUFFER_SIZE
                            else:
                                remaining = file_size - received
                                chunk_size = min(BUFFER_SIZE, remaining)

                            if chunk_size == 0 and not is_stream:
                                break

                            chunk = conn.recv(chunk_size)
                            if not chunk:
                                break

                            f.write(chunk)
                            received += len(chunk)

                            if progress_callback:
                                elapsed = time.time() - start_time
                                speed = (received / (1024 * 1024)) / max(elapsed, 0.001)
                                progress_callback(received, file_size if not is_stream else 0, speed)

                    success = True if is_stream else (received == file_size)

                    if success:
                        conn.sendall(b"OK")
                        logger.info("Dosya başarıyla alındı: %s", save_path)
                    else:
                        conn.sendall(b"NO")
                        logger.error("Dosya tam alınamadı: %d/%d", received, file_size)

                    conn.close()

                    if complete_callback:
                        complete_callback(save_path, success)

                except socket.timeout:
                    continue

            server.close()

        except Exception as e:
            logger.error("Alıcı hatası: %s", e)

    def _get_local_ip(self) -> str:
        """Yerel IP adresini al."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def get_local_ip(self) -> str:
        """Public method for local IP."""
        return self._get_local_ip()

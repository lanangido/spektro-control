"""
uv_protocol.py - Protokol komunikasi serial untuk Shimadzu UVmini-1240.

Refactored dari kode referensi yang SUDAH TERVALIDASI di alat fisik.
Logika inti ENQ/ACK, Protocol A, Protocol B TIDAK diubah dari kode asli.
Protocol B' ditambahkan baru (belum pernah dites ke alat).

Semua komunikasi di-log lewat callback on_raw_data untuk panel debug GUI.
"""

import serial
import time
import logging
from typing import Optional, Callable, List

logger = logging.getLogger(__name__)

# -- Control codes (sesuai manual Chapter 9) -----------------------------------
ENQ = b'\x05'
ACK = b'\x06'
NAK = b'\x15'
EOT = b'\x04'
ESC = b'\x1b'
NUL = b'\x00'

MAX_RETRY = 5

# Label untuk log control codes agar mudah dibaca di panel debug
_CTRL_NAMES = {
    b'\x05': '<ENQ>', b'\x06': '<ACK>', b'\x15': '<NAK>',
    b'\x04': '<EOT>', b'\x1b': '<ESC>', b'\x00': '<NUL>',
}


def _format_byte(b: bytes) -> str:
    """Format 1 byte untuk logging: control code jadi nama, sisanya ascii/hex."""
    if b in _CTRL_NAMES:
        return _CTRL_NAMES[b]
    try:
        ch = b.decode('ascii')
        if ch.isprintable():
            return ch
        return f'<0x{b[0]:02X}>'
    except Exception:
        return f'<0x{b[0]:02X}>'


def _format_bytes(data: bytes) -> str:
    """Format deretan bytes untuk logging."""
    return ''.join(_format_byte(data[i:i+1]) for i in range(len(data)))


class UVProtocol:
    """
    Handler komunikasi serial ke Shimadzu UVmini-1240.

    Penggunaan:
        proto = UVProtocol()
        proto.on_raw_data = my_callback  # Optional: (direction: str, data: bytes) -> None
        proto.connect("COM3")
        if proto.test_connection():
            proto.send_command("w5000")  # Set wavelength 500.0 nm
            value = proto.read_data("d")  # Baca data saat ini
        proto.disconnect()

    Prasyarat: alat HARUS di mode "PC Ctrl" (tombol F4) sebelum connect.
    """

    def __init__(self):
        self._ser: Optional[serial.Serial] = None
        self.on_raw_data: Optional[Callable[[str, bytes], None]] = None
        self._abort_requested: bool = False

    # -- Logging helper --------------------------------------------------------

    def _log_tx(self, data: bytes):
        """Log data yang dikirim ke alat."""
        logger.debug(f"TX: {_format_bytes(data)}")
        if self.on_raw_data:
            self.on_raw_data("TX", data)

    def _log_rx(self, data: bytes):
        """Log data yang diterima dari alat."""
        if data:
            logger.debug(f"RX: {_format_bytes(data)}")
            if self.on_raw_data:
                self.on_raw_data("RX", data)

    def _write(self, data: bytes):
        """Tulis ke serial port dengan logging."""
        self._ser.write(data)
        self._log_tx(data)

    def _read(self, size: int = 1) -> bytes:
        """Baca dari serial port dengan logging."""
        data = self._ser.read(size)
        self._log_rx(data)
        return data

    # -- Koneksi ---------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def connect(self, port: str, baudrate: int = 9600, timeout: float = 3.0):
        """
        Buka koneksi serial ke alat.
        Parameter serial sudah fixed sesuai spec UVmini-1240:
        7 data bits, odd parity, 1 stop bit.
        """
        if self.is_connected:
            self.disconnect()

        self._ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.SEVENBITS,
            parity=serial.PARITY_ODD,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )
        logger.info(f"Serial port {port} opened (baud={baudrate})")

    def disconnect(self):
        """Tutup koneksi serial."""
        if self._ser and self._ser.is_open:
            port_name = self._ser.port
            self._ser.close()
            logger.info(f"Serial port {port_name} closed")
        self._ser = None

    # -- Test koneksi (ENQ/ACK handshake) --------------------------------------

    def test_connection(self) -> bool:
        """
        Kirim ENQ, tunggu ACK. Retry sampai MAX_RETRY untuk NAK maupun timeout.
        Logika PERSIS dari kode referensi tervalidasi.
        """
        if not self.is_connected:
            return False

        for attempt in range(MAX_RETRY):
            self._write(ENQ)
            reply = self._read(1)
            if reply == ACK:
                self._write(EOT)
                logger.info(f"Connection test OK (attempt {attempt + 1})")
                return True
            logger.warning(
                f"ENQ attempt {attempt + 1}/{MAX_RETRY}: "
                f"got {_format_bytes(reply) if reply else 'timeout'}"
            )
            time.sleep(0.3)

        logger.error("Connection test FAILED after max retries")
        return False

    # -- Protocol A: kirim command (write) -------------------------------------

    def send_command(self, command_str: str) -> bool:
        """
        Protocol A: ENQ -> ACK -> [command+NUL] -> ACK -> EOT -> ACK.
        Logika PERSIS dari kode referensi tervalidasi.
        Retry sampai MAX_RETRY di tahap ENQ dan tahap kirim command.
        """
        if not self.is_connected:
            return False

        # Tahap 1: ENQ -> ACK (dengan retry)
        for attempt in range(MAX_RETRY):
            self._write(ENQ)
            reply = self._read(1)
            if reply == ACK:
                break
            logger.warning(
                f"send_command ENQ attempt {attempt + 1}/{MAX_RETRY}: "
                f"got {_format_bytes(reply) if reply else 'timeout'}"
            )
            time.sleep(0.3)
        else:
            logger.error(f"send_command '{command_str}': ENQ failed after max retries")
            return False

        # Tahap 2: kirim command+NUL -> ACK (dengan retry)
        payload = command_str.encode('ascii') + NUL
        for attempt in range(MAX_RETRY):
            self._write(payload)
            reply = self._read(1)
            if reply == ACK:
                break
            logger.warning(
                f"send_command payload attempt {attempt + 1}/{MAX_RETRY}: "
                f"got {_format_bytes(reply) if reply else 'timeout'}"
            )
            time.sleep(0.3)
        else:
            logger.error(f"send_command '{command_str}': payload failed after max retries")
            return False

        # Tahap 3: tunggu EOT dari alat, balas ACK
        reply = self._read(1)
        if reply == EOT:
            self._write(ACK)
            logger.info(f"Command '{command_str}' sent OK")
            return True

        logger.error(
            f"send_command '{command_str}': expected EOT, "
            f"got {_format_bytes(reply) if reply else 'timeout'}"
        )
        return False

    # -- Protocol B: baca 1 data (read) ----------------------------------------

    def read_data(self, command_str: str) -> Optional[str]:
        """
        Protocol B: baca 1 data.
        ENQ->ACK->[cmd+NUL]->ACK->[alat kirim ENQ]->ACK->[data+NUL]->ACK->EOT->ACK.
        Logika PERSIS dari kode referensi tervalidasi.
        """
        if not self.is_connected:
            return None

        # ENQ -> ACK
        self._write(ENQ)
        reply = self._read(1)
        if reply != ACK:
            logger.error(f"read_data: ENQ got {_format_bytes(reply) if reply else 'timeout'}")
            return None

        # Kirim command+NUL -> ACK
        payload = command_str.encode('ascii') + NUL
        self._write(payload)
        reply = self._read(1)
        if reply != ACK:
            logger.error(f"read_data: payload got {_format_bytes(reply) if reply else 'timeout'}")
            return None

        # Tunggu ENQ dari alat -> balas ACK
        reply = self._read(1)
        if reply != ENQ:
            logger.error(f"read_data: expected ENQ from device, got {_format_bytes(reply) if reply else 'timeout'}")
            return None
        self._write(ACK)

        # Baca data sampai NUL
        data_bytes = bytearray()
        while True:
            b = self._read(1)
            if not b or b == NUL:
                break
            data_bytes += b
        self._write(ACK)

        # Tunggu EOT -> balas ACK
        reply = self._read(1)
        if reply == EOT:
            self._write(ACK)
            result = data_bytes.decode('ascii', errors='replace')
            logger.info(f"read_data '{command_str}' -> '{result}'")
            return result

        logger.error(f"read_data: expected EOT, got {_format_bytes(reply) if reply else 'timeout'}")
        return None

    # -- Protocol B': baca BANYAK data (multi-block read) ----------------------

    def abort_bulk_read(self):
        """
        Minta pembatalan read_bulk_data() yang sedang berjalan.
        Saat flag ini aktif, PC akan mengirim ESC (bukan ACK) setelah
        blok berikutnya selesai diterima, sehingga alat membatalkan
        pengiriman data. Sesuai manual Chapter 9 Protocol B'.

        Aman dipanggil dari thread lain (misal GUI thread).
        """
        self._abort_requested = True
        logger.info("abort_bulk_read: abort requested")

    def read_bulk_data(self, command_str: str, max_points: int = 2000,
                       char_timeout: float = 2.0, progress_callback=None) -> Optional[List[str]]:
        """
        Protocol B': baca BANYAK data sekaligus (dipakai command 'f').

        BELUM PERNAH DITES LANGSUNG KE ALAT — implementasi berdasarkan manual
        Chapter 9 Protocol B'. Logging sangat verbose untuk debugging di lab.

        Alur:
        1. ENQ -> ACK -> [cmd+NUL] -> ACK
        2. Alat kirim ENQ -> PC balas ACK
        3. Alat kirim blok data berturut-turut, tiap blok diakhiri NUL:
           - PC kirim ACK setelah tiap blok -> alat lanjut kirim blok berikutnya
           - PC kirim ESC setelah blok -> alat batalkan, komunikasi berakhir
           - Kalau timeout antar-karakter dalam 1 blok -> kirim NAK
        4. Alat kirim EOT setelah semua blok selesai -> PC balas ACK

        Pembatalan (ESC):
        Panggil abort_bulk_read() dari thread lain untuk membatalkan.
        Data yang sudah diterima tetap dikembalikan.

        Args:
            command_str: command string (misal "f0")
            max_points: batas maksimum jumlah data point
            char_timeout: timeout (detik) antar-karakter dalam 1 blok,
                          jika terlampaui kirim NAK sesuai manual

        Returns:
            List string data, atau None jika gagal
        """
        if not self.is_connected:
            return None

        self._abort_requested = False
        logger.info(f"read_bulk_data: starting with command '{command_str}'")

        # Simpan timeout asli, pakai timeout pendek untuk baca per-karakter
        original_timeout = self._ser.timeout

        # ENQ -> ACK
        self._write(ENQ)
        reply = self._read(1)
        if reply != ACK:
            logger.error(f"read_bulk_data: ENQ got {_format_bytes(reply) if reply else 'timeout'}")
            return None

        # Kirim command+NUL -> ACK
        payload = command_str.encode('ascii') + NUL
        self._write(payload)
        reply = self._read(1)
        if reply != ACK:
            logger.error(f"read_bulk_data: payload got {_format_bytes(reply) if reply else 'timeout'}")
            return None

        # Tunggu ENQ dari alat -> balas ACK
        reply = self._read(1)
        if reply != ENQ:
            logger.error(
                f"read_bulk_data: expected ENQ from device, "
                f"got {_format_bytes(reply) if reply else 'timeout'}"
            )
            return None
        self._write(ACK)

        # Baca blok-blok data
        results: List[str] = []
        self._ser.timeout = char_timeout  # timeout pendek untuk deteksi jeda

        try:
            while len(results) < max_points:
                block_data = bytearray()
                nak_sent = False

                while True:
                    b = self._read(1)

                    if not b:
                        # Timeout antar-karakter dalam 1 blok
                        if len(block_data) > 0 and not nak_sent:
                            # Ada data parsial tapi karakter berikutnya tidak datang
                            # -> kirim NAK sesuai manual Chapter 9 Protocol B'
                            logger.warning(
                                f"read_bulk_data: char timeout in block "
                                f"(partial data: {block_data.decode('ascii', errors='replace')}), "
                                f"sending NAK"
                            )
                            self._write(NAK)
                            nak_sent = True
                            continue
                        elif len(block_data) == 0:
                            # Tidak ada data sama sekali — mungkin EOT akan datang
                            # Coba baca sekali lagi dengan timeout normal
                            self._ser.timeout = original_timeout
                            b = self._read(1)
                            self._ser.timeout = char_timeout
                            if b == EOT:
                                self._write(ACK)
                                logger.info(
                                    f"read_bulk_data: EOT received, "
                                    f"total {len(results)} data points"
                                )
                                return results
                            elif not b:
                                logger.error("read_bulk_data: timeout waiting for data/EOT")
                                return results if results else None
                            # Kalau bukan EOT dan bukan timeout, lanjut proses
                            block_data += b
                            continue
                        else:
                            # NAK sudah dikirim tapi tetap timeout
                            logger.error(
                                f"read_bulk_data: persistent timeout after NAK, aborting"
                            )
                            return results if results else None

                    if b == NUL:
                        # Akhir 1 blok data
                        break

                    if b == EOT:
                        # EOT di tengah — semua blok sudah selesai
                        self._write(ACK)
                        logger.info(
                            f"read_bulk_data: EOT received, "
                            f"total {len(results)} data points"
                        )
                        return results

                    block_data += b

                # Blok selesai (NUL diterima), simpan data
                decoded = block_data.decode('ascii', errors='replace')
                results.append(decoded)

                if progress_callback:
                    progress_callback(len(results))

                # Cek apakah ada permintaan abort (ESC)
                if self._abort_requested:
                    self._write(ESC)
                    logger.info(
                        f"read_bulk_data: abort via ESC after block {len(results)}, "
                        f"returning {len(results)} data points collected so far"
                    )
                    return results

                self._write(ACK)
                logger.debug(
                    f"read_bulk_data: block {len(results)} = '{decoded}'"
                )

        finally:
            # Kembalikan timeout asli
            self._ser.timeout = original_timeout

        logger.info(f"read_bulk_data: max_points reached ({max_points})")
        return results

    # -- Convenience: tunggu EOT setelah command scan --------------------------

    def wait_for_eot(self, timeout: float = 600.0) -> bool:
        """
        Tunggu sampai alat mengirim EOT (scan/measurement selesai).
        Dipakai setelah kirim command scan (a/b) via send_command().

        Command 'a' (wavelength scan) dan 'b' (time scan) memicu pengukuran
        di sisi alat. Alat akan mengirim EOT saat pengukuran selesai.
        Selama menunggu, tidak ada data yang dikirim ke PC.

        Args:
            timeout: batas waktu tunggu dalam detik (default 10 menit)

        Returns:
            True jika EOT diterima, False jika timeout
        """
        if not self.is_connected:
            return False

        original_timeout = self._ser.timeout
        self._ser.timeout = timeout
        logger.info(f"wait_for_eot: waiting (timeout={timeout}s)...")

        try:
            reply = self._read(1)
            if reply == EOT:
                self._write(ACK)
                logger.info("wait_for_eot: EOT received, measurement complete")
                return True
            else:
                logger.error(
                    f"wait_for_eot: expected EOT, "
                    f"got {_format_bytes(reply) if reply else 'timeout'}"
                )
                return False
        finally:
            self._ser.timeout = original_timeout

    # -- Utility ---------------------------------------------------------------

    @staticmethod
    def list_ports() -> List[str]:
        """List semua COM port yang tersedia di sistem."""
        import serial.tools.list_ports
        return [p.device for p in serial.tools.list_ports.comports()]

    @staticmethod
    def format_bytes_display(data: bytes) -> str:
        """Format bytes untuk tampilan di panel log."""
        return _format_bytes(data)

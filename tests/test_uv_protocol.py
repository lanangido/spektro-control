"""
test_uv_protocol.py - Unit test untuk protokol UVmini-1240.

Menggunakan serial port palsu (MockSerial) yang mensimulasikan respons alat.
Bisa dijalankan tanpa alat fisik: python -m pytest tests/ -v

Skenario yang ditest:
1. test_connection sukses (ENQ -> ACK)
2. test_connection retry (NAK 2x lalu ACK)
3. test_connection timeout total (tidak pernah balas -> gagal setelah 5x)
4. send_command urutan byte persis (Protocol A)
5. send_command retry pada tahap ENQ
6. send_command retry pada tahap payload
7. send_command gagal total
8. read_data sukses (Protocol B)
9. read_bulk_data sukses (Protocol B')
10. read_bulk_data EOT langsung tanpa data
"""

import pytest
from unittest.mock import patch
from collections import deque

from protocol.uv_protocol import UVProtocol, ENQ, ACK, NAK, EOT, ESC, NUL


# =============================================================================
# MockSerial — serial port palsu yang bisa diprogram responsnya
# =============================================================================

class MockSerial:
    """
    Serial port palsu. Respons diprogram lewat `responses` (deque of bytes).
    Tiap kali `read(1)` dipanggil, ambil 1 item dari depan deque.
    Kalau deque kosong, kembalikan b'' (simulasi timeout).
    Semua data yang ditulis lewat `write()` dicatat di `written`.
    """

    def __init__(self, responses=None):
        self.responses: deque = deque(responses or [])
        self.written: list[bytes] = []
        self.is_open: bool = True
        self.port: str = "MOCK"
        self.timeout: float = 3.0

    def write(self, data: bytes):
        self.written.append(data)

    def read(self, size: int = 1) -> bytes:
        if self.responses:
            return self.responses.popleft()
        return b''  # simulasi timeout

    def close(self):
        self.is_open = False


def make_proto(responses: list[bytes]) -> UVProtocol:
    """Helper: buat UVProtocol dengan MockSerial yang sudah diprogram."""
    proto = UVProtocol()
    proto._ser = MockSerial(responses)
    return proto


# =============================================================================
# TEST: test_connection
# =============================================================================

class TestConnection:
    """Test ENQ/ACK handshake (test_connection)."""

    def test_sukses_langsung(self):
        """ENQ -> ACK di percobaan pertama -> True, lalu kirim EOT."""
        proto = make_proto([ACK])

        result = proto.test_connection()

        assert result is True
        mock: MockSerial = proto._ser
        # Harus kirim: ENQ, lalu EOT setelah dapat ACK
        assert mock.written == [ENQ, EOT]

    def test_retry_nak_lalu_sukses(self):
        """Alat balas NAK 2x, baru ACK di percobaan ke-3 -> True."""
        proto = make_proto([NAK, NAK, ACK])

        result = proto.test_connection()

        assert result is True
        mock: MockSerial = proto._ser
        # Harus kirim ENQ 3x (2x dapat NAK, 1x dapat ACK), lalu EOT
        assert mock.written == [ENQ, ENQ, ENQ, EOT]

    def test_timeout_total_gagal(self):
        """Alat tidak pernah balas (timeout) -> retry 5x lalu False."""
        # Deque kosong = semua read() return b'' (timeout)
        proto = make_proto([])

        result = proto.test_connection()

        assert result is False
        mock: MockSerial = proto._ser
        # Harus kirim ENQ tepat 5x (MAX_RETRY), tidak ada EOT karena gagal
        assert mock.written == [ENQ] * 5

    def test_not_connected(self):
        """Kalau belum connect (serial None), langsung False."""
        proto = UVProtocol()
        assert proto.test_connection() is False

    def test_campuran_timeout_dan_nak(self):
        """Timeout 2x, NAK 1x, lalu ACK -> True di percobaan ke-4."""
        proto = make_proto([
            b'',  # timeout (read returns empty)
            b'',  # timeout
            NAK,  # NAK
            ACK,  # akhirnya ACK
        ])

        result = proto.test_connection()

        assert result is True
        mock: MockSerial = proto._ser
        assert mock.written == [ENQ, ENQ, ENQ, ENQ, EOT]


# =============================================================================
# TEST: send_command (Protocol A)
# =============================================================================

class TestSendCommand:
    """Test Protocol A: ENQ -> ACK -> [cmd+NUL] -> ACK -> EOT -> ACK."""

    def test_sukses_urutan_byte_persis(self):
        """Cek urutan byte yang dikirim persis untuk command w5000."""
        proto = make_proto([
            ACK,  # balasan untuk ENQ
            ACK,  # balasan untuk payload (w5000 + NUL)
            EOT,  # alat kirim EOT setelah selesai proses
        ])

        result = proto.send_command("w5000")

        assert result is True
        mock: MockSerial = proto._ser
        expected_payload = b'w5000' + NUL
        assert mock.written == [ENQ, expected_payload, ACK]

    def test_retry_enq_lalu_sukses(self):
        """NAK di tahap ENQ 2x, baru ACK -> lanjut kirim payload."""
        proto = make_proto([
            NAK,  # ENQ attempt 1 -> NAK
            NAK,  # ENQ attempt 2 -> NAK
            ACK,  # ENQ attempt 3 -> ACK -> lanjut
            ACK,  # balasan payload -> ACK
            EOT,  # alat kirim EOT
        ])

        result = proto.send_command("x")

        assert result is True
        mock: MockSerial = proto._ser
        expected_payload = b'x' + NUL
        # ENQ 3x, lalu payload, lalu ACK (balasan EOT)
        assert mock.written == [ENQ, ENQ, ENQ, expected_payload, ACK]

    def test_retry_payload_lalu_sukses(self):
        """ENQ langsung ACK, tapi payload di-NAK 1x baru ACK."""
        proto = make_proto([
            ACK,  # ENQ -> ACK langsung
            NAK,  # payload attempt 1 -> NAK
            ACK,  # payload attempt 2 -> ACK
            EOT,  # alat kirim EOT
        ])

        result = proto.send_command("w5000")

        assert result is True
        mock: MockSerial = proto._ser
        expected_payload = b'w5000' + NUL
        # ENQ 1x, payload 2x (1x NAK, 1x ACK), lalu ACK balasan EOT
        assert mock.written == [ENQ, expected_payload, expected_payload, ACK]

    def test_enq_gagal_total(self):
        """ENQ selalu timeout (5x) -> False, payload tidak pernah dikirim."""
        proto = make_proto([])  # semua timeout

        result = proto.send_command("w5000")

        assert result is False
        mock: MockSerial = proto._ser
        # Hanya ENQ 5x, tidak ada payload
        assert mock.written == [ENQ] * 5

    def test_payload_gagal_total(self):
        """ENQ OK, tapi payload selalu NAK (5x) -> False."""
        proto = make_proto([
            ACK,  # ENQ -> ACK
            NAK, NAK, NAK, NAK, NAK,  # payload 5x NAK
        ])

        result = proto.send_command("w5000")

        assert result is False
        mock: MockSerial = proto._ser
        expected_payload = b'w5000' + NUL
        # ENQ 1x, payload 5x
        assert mock.written == [ENQ] + [expected_payload] * 5

    def test_eot_tidak_datang(self):
        """ENQ OK, payload OK, tapi alat tidak kirim EOT -> False."""
        proto = make_proto([
            ACK,  # ENQ
            ACK,  # payload
            b'',  # harusnya EOT tapi timeout
        ])

        result = proto.send_command("w5000")

        assert result is False

    def test_not_connected(self):
        """Kalau belum connect, langsung False."""
        proto = UVProtocol()
        assert proto.send_command("w5000") is False


# =============================================================================
# TEST: read_data (Protocol B)
# =============================================================================

class TestReadData:
    """Test Protocol B: baca 1 data."""

    def test_sukses_baca_data(self):
        """
        Alur lengkap:
        PC: ENQ -> Alat: ACK
        PC: cmd+NUL -> Alat: ACK
        Alat: ENQ -> PC: ACK
        Alat: data bytes + NUL -> PC: ACK
        Alat: EOT -> PC: ACK
        """
        proto = make_proto([
            ACK,            # balasan ENQ
            ACK,            # balasan payload (d + NUL)
            ENQ,            # alat kirim ENQ
            b'0', b'.', b'5', b'2', b'3',  # data: "0.523"
            NUL,            # akhir data
            EOT,            # alat kirim EOT
        ])

        result = proto.read_data("d")

        assert result == "0.523"
        mock: MockSerial = proto._ser
        expected_payload = b'd' + NUL
        # PC kirim: ENQ, payload, ACK (balas ENQ alat), ACK (setelah data), ACK (balas EOT)
        assert mock.written == [ENQ, expected_payload, ACK, ACK, ACK]

    def test_enq_ditolak(self):
        """Alat balas NAK saat ENQ -> None."""
        proto = make_proto([NAK])

        result = proto.read_data("d")

        assert result is None

    def test_payload_ditolak(self):
        """ENQ OK tapi payload di-NAK -> None."""
        proto = make_proto([ACK, NAK])

        result = proto.read_data("d")

        assert result is None

    def test_alat_tidak_kirim_enq(self):
        """ENQ OK, payload OK, tapi alat tidak kirim ENQ balik -> None."""
        proto = make_proto([ACK, ACK, b''])

        result = proto.read_data("d")

        assert result is None

    def test_not_connected(self):
        """Belum connect -> None."""
        proto = UVProtocol()
        assert proto.read_data("d") is None


# =============================================================================
# TEST: read_bulk_data (Protocol B')
# =============================================================================

class TestReadBulkData:
    """Test Protocol B': baca banyak data."""

    def test_sukses_3_blok(self):
        """
        3 blok data lalu EOT.
        Tiap blok diakhiri NUL, PC kirim ACK per blok.
        """
        proto = make_proto([
            ACK,            # balasan ENQ
            ACK,            # balasan payload
            ENQ,            # alat kirim ENQ
            # Blok 1: "0.100"
            b'0', b'.', b'1', b'0', b'0', NUL,
            # Blok 2: "0.200"
            b'0', b'.', b'2', b'0', b'0', NUL,
            # Blok 3: "0.300"
            b'0', b'.', b'3', b'0', b'0', NUL,
            # Selesai
            EOT,
        ])

        result = proto.read_bulk_data("f0", char_timeout=0.1)

        assert result == ["0.100", "0.200", "0.300"]

    def test_eot_langsung_tanpa_data(self):
        """Alat kirim EOT langsung setelah handshake -> list kosong."""
        proto = make_proto([
            ACK,  # ENQ
            ACK,  # payload
            ENQ,  # alat ENQ
            # Tidak ada blok data, langsung:
            b'',  # timeout pada char_timeout (block kosong)
            EOT,  # EOT pada original_timeout
        ])

        result = proto.read_bulk_data("f0", char_timeout=0.1)

        assert result == []

    def test_eot_di_tengah_blok(self):
        """EOT diterima sebelum NUL (di antara blok) -> return data yg sudah ada."""
        proto = make_proto([
            ACK,  # ENQ
            ACK,  # payload
            ENQ,  # alat ENQ
            # Blok 1
            b'1', b'.', b'0', NUL,
            # Langsung EOT (bukan blok baru)
            EOT,
        ])

        result = proto.read_bulk_data("f0", char_timeout=0.1)

        assert result == ["1.0"]

    def test_enq_gagal(self):
        """ENQ di-NAK -> None."""
        proto = make_proto([NAK])

        result = proto.read_bulk_data("f0")

        assert result is None

    def test_not_connected(self):
        """Belum connect -> None."""
        proto = UVProtocol()
        assert proto.read_bulk_data("f0") is None

    def test_nak_saat_char_timeout_dalam_blok(self):
        """
        Skenario: sedang terima blok data karakter demi karakter,
        tiba-tiba karakter berikutnya tidak datang (timeout).
        Harus kirim NAK (bukan dianggap gagal total).
        Setelah NAK, alat kirim ulang sisa data -> blok selesai normal.

        Flow:
        - Terima '0', '.' (2 karakter) -> timeout -> kirim NAK
        - Alat kirim ulang: '5', '2', '3' + NUL -> blok selesai
        - ACK -> EOT -> ACK
        """
        proto = make_proto([
            ACK,            # balasan ENQ
            ACK,            # balasan payload
            ENQ,            # alat kirim ENQ
            # Blok 1: data parsial lalu timeout
            b'0', b'.',     # 2 karakter datang
            b'',            # timeout! -> harus kirim NAK
            # Setelah NAK, alat kirim lanjutan/ulang
            b'5', b'2', b'3', NUL,
            # Selesai
            EOT,
        ])

        result = proto.read_bulk_data("f0", char_timeout=0.1)

        assert result is not None
        assert len(result) == 1
        # Data yang terkumpul: '0.' + '523' = '0.523'
        assert result[0] == "0.523"

        # Verifikasi NAK benar-benar dikirim
        mock: MockSerial = proto._ser
        assert NAK in mock.written, "NAK harus dikirim saat char timeout dalam blok"

    def test_nak_persistent_timeout_lalu_gagal(self):
        """
        Skenario: char timeout -> kirim NAK -> timeout lagi (persistent).
        Harus return data yang sudah ada (atau None jika belum ada).
        Tidak boleh hang selamanya.
        """
        proto = make_proto([
            ACK,        # ENQ
            ACK,        # payload
            ENQ,        # alat ENQ
            # Blok 1: data parsial
            b'1', b'.',
            b'',        # timeout -> NAK
            b'',        # masih timeout setelah NAK -> abort
        ])

        result = proto.read_bulk_data("f0", char_timeout=0.1)

        # Belum ada blok yang selesai, jadi None
        assert result is None
        mock: MockSerial = proto._ser
        assert NAK in mock.written

    def test_esc_abort_di_tengah_transfer(self):
        """
        Skenario: PC ingin membatalkan penerimaan data di tengah jalan
        (misal user klik Cancel di GUI saat sedang tarik data scan besar).
        PC kirim ESC (bukan ACK) setelah blok selesai diterima.
        Data yang sudah diterima tetap dikembalikan.

        Flow:
        - Blok 1 diterima OK
        - abort_bulk_read() dipanggil (set flag) saat NUL blok 1 dibaca
        - Setelah blok 1 selesai, kirim ESC (bukan ACK)
        - Return ['0.100'] (data blok 1 yang sudah diterima)
        """
        # MockSerial khusus: set abort flag saat NUL pertama dibaca
        class AbortOnFirstNul(MockSerial):
            def __init__(self, responses, proto_ref):
                super().__init__(responses)
                self._proto_ref = proto_ref
                self._nul_count = 0

            def read(self, size=1):
                data = super().read(size)
                if data == NUL:
                    self._nul_count += 1
                    if self._nul_count == 1:
                        # Simulasi: user klik Cancel tepat saat blok 1 selesai
                        self._proto_ref._abort_requested = True
                return data

        proto = UVProtocol()
        mock = AbortOnFirstNul([
            ACK,            # balasan ENQ
            ACK,            # balasan payload
            ENQ,            # alat kirim ENQ
            # Blok 1: "0.100"
            b'0', b'.', b'1', b'0', b'0', NUL,
            # Blok 2 seharusnya ada tapi tidak akan dibaca karena abort
            b'0', b'.', b'2', b'0', b'0', NUL,
            EOT,
        ], proto)
        proto._ser = mock

        result = proto.read_bulk_data("f0", char_timeout=0.1)

        # Blok 1 sudah diterima sebelum abort di-cek
        assert result == ["0.100"]

        # Verifikasi ESC dikirim (bukan ACK) setelah blok 1
        assert ESC in mock.written, "ESC harus dikirim saat abort requested"
        # written seharusnya: [ENQ, payload, ACK(balas ENQ alat), ESC]
        assert mock.written[-1] == ESC, "Byte terakhir yang dikirim harus ESC"

    def test_abort_bulk_read_method(self):
        """Test bahwa abort_bulk_read() set flag dengan benar."""
        proto = UVProtocol()
        assert proto._abort_requested is False
        proto.abort_bulk_read()
        assert proto._abort_requested is True


# =============================================================================
# TEST: wait_for_eot
# =============================================================================

class TestWaitForEot:
    """Test tunggu EOT setelah scan."""

    def test_eot_diterima(self):
        """Alat kirim EOT -> True."""
        proto = make_proto([EOT])

        result = proto.wait_for_eot(timeout=1.0)

        assert result is True
        mock: MockSerial = proto._ser
        assert ACK in mock.written

    def test_timeout(self):
        """Tidak ada EOT (timeout) -> False."""
        proto = make_proto([])

        result = proto.wait_for_eot(timeout=0.1)

        assert result is False

    def test_not_connected(self):
        proto = UVProtocol()
        assert proto.wait_for_eot() is False


# =============================================================================
# TEST: logging callback
# =============================================================================

class TestLogging:
    """Test bahwa on_raw_data callback dipanggil dengan benar."""

    def test_callback_dipanggil(self):
        """Pastikan TX dan RX di-log lewat callback."""
        log_entries = []

        def my_callback(direction, data):
            log_entries.append((direction, data))

        proto = make_proto([ACK])
        proto.on_raw_data = my_callback

        proto.test_connection()

        # Harus ada log TX (ENQ) dan RX (ACK) dan TX (EOT)
        tx_entries = [e for e in log_entries if e[0] == "TX"]
        rx_entries = [e for e in log_entries if e[0] == "RX"]
        assert len(tx_entries) >= 2  # ENQ + EOT
        assert len(rx_entries) >= 1  # ACK
        assert tx_entries[0] == ("TX", ENQ)
        assert rx_entries[0] == ("RX", ACK)


# =============================================================================
# TEST: is_connected property
# =============================================================================

class TestIsConnected:
    """Test property is_connected."""

    def test_awal_false(self):
        proto = UVProtocol()
        assert proto.is_connected is False

    def test_setelah_mock_true(self):
        proto = make_proto([])
        assert proto.is_connected is True

    def test_setelah_close_false(self):
        proto = make_proto([])
        proto._ser.close()
        assert proto.is_connected is False

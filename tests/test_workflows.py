"""
test_workflows.py - Integration test untuk workflow Tahap 3-6.

Test command parameter formatting dan urutan pemanggilan command
menggunakan MockSerial (tanpa alat fisik).

Skenario:
1. Command formatting (parameter w, v, x, c, a, b)
2. Wavelength scan workflow lengkap (a → EOT → f)
3. Time scan workflow lengkap (b → EOT → f)
"""

import pytest
from collections import deque

from protocol.uv_protocol import UVProtocol, ENQ, ACK, NAK, EOT, NUL


# ═════════════════════════════════════════════════════════════════════════════
# MockSerial (sama dengan test_uv_protocol.py)
# ═════════════════════════════════════════════════════════════════════════════

class MockSerial:
    """Serial port palsu. Respons diprogram lewat deque."""

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
        return b''

    def close(self):
        self.is_open = False


def make_proto(responses: list[bytes]) -> UVProtocol:
    """Buat UVProtocol dengan MockSerial."""
    proto = UVProtocol()
    proto._ser = MockSerial(responses)
    return proto


def make_protocol_a_responses():
    """Respons standar untuk 1x Protocol A yang sukses: ENQ→ACK, payload→ACK, EOT."""
    return [ACK, ACK, EOT]


def make_protocol_b_prime_responses(data_blocks: list[str]):
    """
    Buat respons MockSerial untuk Protocol B' yang sukses.
    ENQ→ACK, payload→ACK, alat ENQ, lalu tiap blok data + NUL, akhirnya EOT.
    """
    responses = [ACK, ACK, ENQ]
    for block in data_blocks:
        for ch in block:
            responses.append(ch.encode('ascii'))
        responses.append(NUL)
    responses.append(EOT)
    return responses


# ═════════════════════════════════════════════════════════════════════════════
# TEST: Command parameter formatting (Tahap 3-4)
# ═════════════════════════════════════════════════════════════════════════════

class TestCommandFormatting:
    """Test bahwa parameter command diformat persis sesuai spec."""

    def test_goto_wl_500nm(self):
        """500.0 nm → command 'w5000' (wavelength x10)."""
        proto = make_proto(make_protocol_a_responses())

        wl = 500.0
        cmd = f"w{int(wl * 10)}"
        assert cmd == "w5000"

        ok = proto.send_command(cmd)
        assert ok is True

        mock: MockSerial = proto._ser
        # Payload yang dikirim harus b'w5000\x00'
        assert mock.written[1] == b'w5000' + NUL

    def test_goto_wl_190nm(self):
        """190.0 nm → command 'w1900' (batas bawah)."""
        proto = make_proto(make_protocol_a_responses())

        wl = 190.0
        cmd = f"w{int(wl * 10)}"
        assert cmd == "w1900"

        ok = proto.send_command(cmd)
        assert ok is True
        assert proto._ser.written[1] == b'w1900' + NUL

    def test_goto_wl_1100nm(self):
        """1100.0 nm → command 'w11000' (batas atas)."""
        proto = make_proto(make_protocol_a_responses())

        wl = 1100.0
        cmd = f"w{int(wl * 10)}"
        assert cmd == "w11000"

        ok = proto.send_command(cmd)
        assert ok is True
        assert proto._ser.written[1] == b'w11000' + NUL

    def test_goto_wl_decimal(self):
        """325.5 nm → command 'w3255'."""
        proto = make_proto(make_protocol_a_responses())

        wl = 325.5
        cmd = f"w{int(wl * 10)}"
        assert cmd == "w3255"

        ok = proto.send_command(cmd)
        assert ok is True
        assert proto._ser.written[1] == b'w3255' + NUL

    def test_mode_abs(self):
        """Mode Abs → command 'v0'."""
        proto = make_proto(make_protocol_a_responses())
        ok = proto.send_command("v0")
        assert ok is True
        assert proto._ser.written[1] == b'v0' + NUL

    def test_mode_transmittance(self):
        """Mode T% → command 'v1'."""
        proto = make_proto(make_protocol_a_responses())
        ok = proto.send_command("v1")
        assert ok is True
        assert proto._ser.written[1] == b'v1' + NUL

    def test_mode_energy(self):
        """Mode Energy → command 'v2'."""
        proto = make_proto(make_protocol_a_responses())
        ok = proto.send_command("v2")
        assert ok is True
        assert proto._ser.written[1] == b'v2' + NUL

    def test_auto_zero(self):
        """Auto Zero → command 'x'."""
        proto = make_proto(make_protocol_a_responses())
        ok = proto.send_command("x")
        assert ok is True
        assert proto._ser.written[1] == b'x' + NUL

    def test_baseline_190_1100(self):
        """Baseline 190-1100 nm → command 'c1900,11000'."""
        proto = make_proto(make_protocol_a_responses())

        start, end = 190.0, 1100.0
        cmd = f"c{int(start * 10)},{int(end * 10)}"
        assert cmd == "c1900,11000"

        ok = proto.send_command(cmd)
        assert ok is True
        assert proto._ser.written[1] == b'c1900,11000' + NUL

    def test_baseline_200_800(self):
        """Baseline 200-800 nm → command 'c2000,8000'."""
        proto = make_proto(make_protocol_a_responses())

        start, end = 200.0, 800.0
        cmd = f"c{int(start * 10)},{int(end * 10)}"
        assert cmd == "c2000,8000"

        ok = proto.send_command(cmd)
        assert ok is True
        assert proto._ser.written[1] == b'c2000,8000' + NUL


# ═════════════════════════════════════════════════════════════════════════════
# TEST: Wavelength Scan workflow (Tahap 5)
# ═════════════════════════════════════════════════════════════════════════════

class TestWavelengthScanWorkflow:
    """
    Test alur lengkap wavelength scan:
    1. send_command("a{start},{end},{speed}") — Protocol A
    2. wait_for_eot() — tunggu scan selesai
    3. read_bulk_data("f0") — tarik data — Protocol B'
    """

    def test_scan_190_800_speed3(self):
        """Full workflow: a1900,8000,3 → EOT → f0 → 3 data points."""
        all_responses = (
            # Step 1: send_command("a1900,8000,3") — Protocol A
            make_protocol_a_responses()
            # Step 2: wait_for_eot() — alat kirim EOT saat scan selesai
            + [EOT]
            # Step 3: read_bulk_data("f0") — Protocol B'
            + make_protocol_b_prime_responses(["0.100", "0.200", "0.300"])
        )
        proto = make_proto(all_responses)

        # Step 1: Kirim command scan
        start, end, speed = 190.0, 800.0, 3
        cmd = f"a{int(start*10)},{int(end*10)},{speed}"
        assert cmd == "a1900,8000,3"

        ok = proto.send_command(cmd)
        assert ok is True

        # Step 2: Tunggu EOT
        eot = proto.wait_for_eot(timeout=1.0)
        assert eot is True

        # Step 3: Tarik data
        data = proto.read_bulk_data("f0", char_timeout=0.1)
        assert data is not None
        assert data == ["0.100", "0.200", "0.300"]

    def test_scan_400_700_speed1(self):
        """Scan 400-700nm speed 1 → command a4000,7000,1."""
        all_responses = (
            make_protocol_a_responses()
            + [EOT]
            + make_protocol_b_prime_responses(["1.234", "2.345"])
        )
        proto = make_proto(all_responses)

        cmd = f"a{int(400.0*10)},{int(700.0*10)},{1}"
        assert cmd == "a4000,7000,1"

        ok = proto.send_command(cmd)
        assert ok is True

        eot = proto.wait_for_eot(timeout=1.0)
        assert eot is True

        data = proto.read_bulk_data("f0", char_timeout=0.1)
        assert data == ["1.234", "2.345"]

    def test_scan_command_gagal(self):
        """Kalau send_command gagal, workflow berhenti di step 1."""
        proto = make_proto([NAK, NAK, NAK, NAK, NAK])  # ENQ selalu NAK

        ok = proto.send_command("a1900,8000,3")
        assert ok is False
        # Tidak lanjut ke wait_for_eot

    def test_scan_eot_timeout(self):
        """Kalau EOT tidak datang (scan timeout), workflow berhenti di step 2."""
        all_responses = make_protocol_a_responses() + [b'']  # timeout saat tunggu EOT
        proto = make_proto(all_responses)

        ok = proto.send_command("a1900,8000,3")
        assert ok is True

        eot = proto.wait_for_eot(timeout=0.1)
        assert eot is False
        # Tidak lanjut ke read_bulk_data

    def test_scan_data_pull_gagal(self):
        """Kalau read_bulk_data gagal, return None."""
        all_responses = (
            make_protocol_a_responses()
            + [EOT]
            + [NAK]  # ENQ saat f0 → NAK
        )
        proto = make_proto(all_responses)

        ok = proto.send_command("a1900,8000,3")
        assert ok is True

        eot = proto.wait_for_eot(timeout=1.0)
        assert eot is True

        data = proto.read_bulk_data("f0")
        assert data is None


# ═════════════════════════════════════════════════════════════════════════════
# TEST: Time Scan workflow (Tahap 6)
# ═════════════════════════════════════════════════════════════════════════════

class TestTimeScanWorkflow:
    """
    Test alur lengkap time scan:
    1. send_command("b{durasi},{satuan}") — Protocol A
    2. wait_for_eot() — tunggu pengukuran selesai
    3. read_bulk_data("f0") — tarik data — Protocol B'
    """

    def test_time_scan_30_detik(self):
        """b30,0 = 30 detik → full workflow."""
        all_responses = (
            make_protocol_a_responses()
            + [EOT]
            + make_protocol_b_prime_responses(["0.500", "0.501", "0.499"])
        )
        proto = make_proto(all_responses)

        duration, unit = 30, 0  # 30 detik
        cmd = f"b{duration},{unit}"
        assert cmd == "b30,0"

        ok = proto.send_command(cmd)
        assert ok is True

        eot = proto.wait_for_eot(timeout=1.0)
        assert eot is True

        data = proto.read_bulk_data("f0", char_timeout=0.1)
        assert data == ["0.500", "0.501", "0.499"]

    def test_time_scan_5_menit(self):
        """b5,1 = 5 menit → command format benar."""
        all_responses = (
            make_protocol_a_responses()
            + [EOT]
            + make_protocol_b_prime_responses(["1.000", "1.001"])
        )
        proto = make_proto(all_responses)

        duration, unit = 5, 1  # 5 menit
        cmd = f"b{duration},{unit}"
        assert cmd == "b5,1"

        ok = proto.send_command(cmd)
        assert ok is True
        # Verifikasi payload bytes
        assert proto._ser.written[1] == b'b5,1' + NUL

        eot = proto.wait_for_eot(timeout=1.0)
        assert eot is True

        data = proto.read_bulk_data("f0", char_timeout=0.1)
        assert data == ["1.000", "1.001"]

    def test_time_scan_1_detik_minimal(self):
        """b1,0 = 1 detik (durasi minimal)."""
        all_responses = (
            make_protocol_a_responses()
            + [EOT]
            + make_protocol_b_prime_responses(["0.123"])
        )
        proto = make_proto(all_responses)

        cmd = f"b{1},{0}"
        assert cmd == "b1,0"

        ok = proto.send_command(cmd)
        assert ok is True
        assert proto._ser.written[1] == b'b1,0' + NUL

    def test_time_scan_6500_menit_maximal(self):
        """b6500,1 = 6500 menit (durasi maksimal)."""
        all_responses = make_protocol_a_responses()
        proto = make_proto(all_responses)

        cmd = f"b{6500},{1}"
        assert cmd == "b6500,1"

        ok = proto.send_command(cmd)
        assert ok is True
        assert proto._ser.written[1] == b'b6500,1' + NUL

    def test_time_scan_command_gagal(self):
        """Command b gagal → workflow berhenti."""
        proto = make_proto([NAK] * 5)

        ok = proto.send_command("b30,0")
        assert ok is False


# ═════════════════════════════════════════════════════════════════════════════
# TEST: Baca Data command d (Tahap 3)
# ═════════════════════════════════════════════════════════════════════════════

class TestReadDataWorkflow:
    """Test baca data tunggal via command d (Protocol B)."""

    def test_baca_absorbance(self):
        """Command d → baca nilai absorbance '0.523'."""
        proto = make_proto([
            ACK,                            # ENQ
            ACK,                            # payload d+NUL
            ENQ,                            # alat kirim ENQ
            b'0', b'.', b'5', b'2', b'3',  # data
            NUL,                            # akhir data
            EOT,                            # selesai
        ])

        result = proto.read_data("d")
        assert result == "0.523"
        # Coba parse sebagai float (seperti yang dilakukan GUI)
        assert float(result) == pytest.approx(0.523)

    def test_baca_transmittance(self):
        """Command d bisa return nilai T% juga."""
        proto = make_proto([
            ACK, ACK, ENQ,
            b'9', b'5', b'.', b'3', b'0',
            NUL, EOT,
        ])

        result = proto.read_data("d")
        assert result == "95.30"
        assert float(result) == pytest.approx(95.30)


# ═════════════════════════════════════════════════════════════════════════════
# TEST: Data parsing helper (simulasi _render_scan_result)
# ═════════════════════════════════════════════════════════════════════════════

class TestDataParsing:
    """Test parsing data string dari Protocol B' ke float values."""

    def test_parse_simple_floats(self):
        """Data string sederhana → list of floats."""
        data = ["0.100", "0.200", "0.300"]
        y = [float(d.strip()) for d in data]
        assert y == [0.1, 0.2, 0.3]

    def test_generate_wavelength_axis(self):
        """Generate sumbu X wavelength dari start/end/n_points."""
        start, end = 190.0, 800.0
        n = 4
        step = (end - start) / (n - 1)
        x = [start + i * step for i in range(n)]
        assert x == pytest.approx([190.0, 393.333, 596.667, 800.0], rel=1e-2)

    def test_generate_time_axis(self):
        """Generate sumbu X waktu dari total_seconds/n_points."""
        total_seconds = 30  # 30 detik
        n = 4
        step = total_seconds / (n - 1)
        x = [0 + i * step for i in range(n)]
        assert x == pytest.approx([0.0, 10.0, 20.0, 30.0])

    def test_parse_comma_separated(self):
        """Kalau data format 'wl,value', ambil value (angka terakhir)."""
        raw = "500.0,0.523"
        parts = raw.strip().split(',')
        value = float(parts[-1])
        assert value == pytest.approx(0.523)

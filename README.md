# Spektro-Control 🔬

**Spektro-Control** adalah perangkat lunak antarmuka modern (GUI) berbasis desktop untuk mengontrol dan membaca data dari instrumen spektrofotometer **Shimadzu UVmini-1240**.

Aplikasi ini dirancang sebagai pengganti atau alternatif dari perangkat lunak kontrol bawaan (seperti UVProbe), dengan fokus utama pada **kemudahan penggunaan (Plug-and-Play)**, antarmuka modern yang responsif, dan alur kerja (*workflow*) yang dioptimalkan untuk keperluan analisis di laboratorium.

---

## 🚀 Fitur Utama (Features)

*   **🔌 Koneksi Cerdas (Auto-Connect)**: Tidak perlu lagi pusing memilih COM port. Aplikasi akan secara diam-diam (di *background*) memindai seluruh port USB/Serial yang aktif dan melakukan *handshake* otomatis ke instrumen. Cukup colok kabel, dan aplikasi langsung terhubung!
*   **🌍 Bilingual (Dua Bahasa)**: Dukungan penuh untuk pergantian bahasa secara langsung (Indonesia & English) tanpa perlu me-*restart* aplikasi.
*   **🎨 Tema Modern (Dark/Light Mode)**: Antarmuka cantik yang dirancang menggunakan palet warna khusus, mendukung mode Gelap (Dark Mode) untuk mengurangi kelelahan mata, dan mode Terang (Light Mode).
*   **📊 Analisis Real-Time**:
    *   **Photometric Mode**: Baca data absorbansi / transmitansi pada panjang gelombang tertentu.
    *   **Wavelength Scan**: Pindai sampel melalui spektrum panjang gelombang dan lihat grafik yang terbentuk secara langsung (*live plotting*).
    *   **Time Scan**: Pantau kinetika reaksi atau perubahan absorbansi seiring waktu.
*   **📁 Manajemen Data**: Ekspor hasil pembacaan spektrum dan kinetika ke dalam format *Spreadsheet* (`.csv`) atau simpan grafiknya langsung sebagai gambar resolusi tinggi (`.png`).
*   **🖨️ Cetak Langsung (Printing)**: Deteksi printer sistem dan kemampuan untuk mengirim *log* atau grafik secara langsung ke mesin cetak fisik.
*   **🛡️ Anti-Panik & Error Handling**: Setiap interaksi serial (pengiriman data, GOTO Wavelength, kalibrasi Auto-Zero/Baseline) dilindungi dengan mekanisme perlindungan *error* (Alert System) yang elegan, mencegah aplikasi macet / *freeze* ketika alat gagal merespons.

---

## 💻 Keterangan Bahasa Pemrograman & Teknologi (Tech Stack)

Aplikasi ini dikembangkan sepenuhnya menggunakan ekosistem **Python** untuk keandalan dan fleksibilitas di berbagai sistem operasi (Windows, Linux, macOS).

*   **Bahasa Pemrograman**: `Python 3.11+`
*   **Framework GUI**: `PySide6` (Binding resmi Qt6 untuk Python), digunakan untuk membangun seluruh arsitektur antarmuka dan *multithreading* (QThread, QTimer).
*   **Visualisasi Data**: `pyqtgraph` (Library graphing super cepat berbasis NumPy) untuk merender grafik spektrum dan kinetika secara langsung dengan frame rate tinggi.
*   **Komunikasi Hardware**: `pyserial` (Mengelola komunikasi RS-232 / COM Port serial dengan protokol ENQ/ACK Shimadzu).

### Struktur Repositori
*   `/ui/`: Berisi logika tampilan (MainWindow, Dialogs, Themes) dan lokalisasi bahasa (`strings.py`).
*   `/protocol/`: Berisi implementasi protokol komunikasi serial *low-level* Shimadzu (`uv_protocol.py`).
*   `main.py`: Titik masuk utama aplikasi (Entry point).
*   `requirements.txt`: Daftar dependensi library Python.

---

## ⚙️ Panduan Instalasi (Installation)

1.  **Clone repositori ini:**
    ```bash
    git clone https://github.com/username/spektro-control.git
    cd spektro-control
    ```

2.  **Buat Virtual Environment (Sangat Disarankan):**
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Instal library yang dibutuhkan:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🏃 Panduan Penggunaan (Usage)

Setelah instalasi selesai dan instrumen UVmini-1240 Anda telah terhubung ke PC via kabel RS-232/USB-to-Serial:

1.  Pastikan instrumen Shimadzu menyala dan berada dalam mode **PC Ctrl** (biasanya dengan menekan tombol **F4** di panel alat).
2.  Jalankan aplikasi dari terminal:
    ```bash
    python main.py
    ```
3.  Aplikasi akan otomatis mencari dan mengunci koneksi dengan instrumen. Anda siap menganalisis sampel!

*(Untuk pengaturan COM Port manual, Anda dapat mengaksesnya melalui menu bar: **Instrument > Advanced Connection...**)*

---
*Dibuat untuk memudahkan analis laboratorium — Happy Science!* 🧪

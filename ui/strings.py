"""
strings.py - Teks UI terpusat untuk Spektro-Control.

Semua teks yang tampil di GUI ditaruh di sini, diorganisasi per bahasa.
Toggle bahasa cukup ganti key bahasa aktif, tidak perlu edit tiap widget.

Istilah teknis dari alat fisik (GOTO WL, A-Z, B-L, Abs, T%, Energy)
TETAP SAMA di kedua bahasa — bukan teks yang perlu diterjemahkan.
"""

STRINGS = {
    # ══════════════════════════════════════════════════════════════════════
    # BAHASA INDONESIA
    # ══════════════════════════════════════════════════════════════════════
    "id": {
        # -- Window --
        "window_title": "Spektro-Control \u2014 UVmini-1240",

        # -- Menu bar --
        "menu_file": "File",
        "menu_instrument": "Instrumen",
        "menu_tools": "Alat",
        "menu_export_csv": "Export CSV...",
        "menu_exit": "Keluar",
        "menu_conn_info": "Info Koneksi",
        "menu_settings": "Pengaturan...",

        # -- Toggle tema --
        "theme_to_dark": "\U0001f319  Dark Mode",
        "theme_to_light": "\u2600  Light Mode",

        # -- Toggle bahasa --
        "lang_to_en": "\U0001f310 English",
        "lang_to_id": "\U0001f310 Bahasa",

        # -- Panel: Koneksi Serial --
        "grp_connection": "KONEKSI SERIAL",
        "lbl_com_port": "COM Port:",
        "btn_connect": "Connect",
        "btn_disconnect": "Disconnect",
        "status_disconnected": "Disconnected",
        "status_connected": "Terhubung",

        # -- Panel: Mode Pengukuran --
        "grp_mode": "MODE PENGUKURAN",
        "lbl_mode": "Mode:",

        # -- Panel: GOTO Wavelength --
        "grp_goto_wl": "GOTO WAVELENGTH",
        "lbl_wavelength": "Wavelength (nm):",
        "btn_goto_wl": "GOTO WL",

        # -- Panel: Kalibrasi --
        "grp_calibration": "KALIBRASI",
        "btn_auto_zero": "Auto Zero (A-Z)",
        "lbl_bl_start": "B-L Start (nm):",
        "lbl_bl_end": "B-L End (nm):",
        "btn_baseline": "Baseline (B-L)",

        # -- Panel: Baca Data --
        "grp_read_data": "BACA DATA",
        "btn_read_data": "Baca Nilai (d)",

        # -- Panel: Wavelength Scan --
        "grp_wscan": "WAVELENGTH SCAN",
        "lbl_scan_start": "Start (nm):",
        "lbl_scan_end": "End (nm):",
        "lbl_speed": "Speed:",
        "btn_start_wscan": "\u25b6  Start Scan",
        "progress_scanning": "Scanning...",

        # -- Panel: Time Scan --
        "grp_tscan": "TIME SCAN",
        "lbl_duration": "Durasi:",
        "lbl_unit": "Satuan:",
        "unit_seconds": "Detik",
        "unit_minutes": "Menit",
        "btn_start_tscan": "\u25b6  Start Time Scan",
        "progress_measuring": "Measuring...",

        # -- Export --
        "btn_export_csv": "Export CSV",
        "btn_export_graph": "Export Grafik",

        # -- Tabel --
        "header_wavelength": "Wavelength (nm)",
        "header_value": "Value",
        "header_time": "Time (s)",

        # -- Tab --
        "tab_data": "Data",
        "tab_log": "Log Komunikasi",

        # -- Log --
        "log_placeholder": "Log komunikasi serial akan muncul di sini...",

        # -- Status bar / notifikasi --
        "msg_ready": "Ready \u2014 Pilih COM port dan klik Connect",
        "msg_connecting": "Connecting ke {port}...",
        "msg_connected": "Terhubung ke {port}",
        "msg_disconnected": "Disconnected",
        "msg_error_no_port": "Error: pilih COM port dulu",
        "msg_connect_ok": "Terhubung ke {port} \u2014 ENQ/ACK OK",
        "msg_connect_error": "Connect error: {err}",
        "msg_goto_wl_progress": "GOTO WL {wl} nm...",
        "msg_goto_wl_ok": "Wavelength set ke {wl} nm",
        "msg_set_mode_progress": "Set mode {label}...",
        "msg_set_mode_ok": "Mode set ke {label}",
        "msg_auto_zero_progress": "A-Z (Auto Zero)...",
        "msg_auto_zero_ok": "Auto Zero selesai",
        "msg_baseline_progress": "B-L (Baseline) {start}\u2013{end} nm...",
        "msg_baseline_ok": "Baseline correction selesai ({start}\u2013{end} nm)",
        "msg_read_progress": "Membaca data...",
        "msg_read_value": "Nilai: {val}",
        "msg_wscan_progress": "Wavelength Scan {start}\u2013{end} nm, speed {speed}...",
        "msg_wscan_waiting": "W-Scan: menunggu alat selesai scan...",
        "msg_wscan_pulling": "W-Scan: menarik data hasil scan via 'f0'...",
        "msg_wscan_ok": "Scan selesai: {n} titik data",
        "msg_tscan_progress": "Time Scan: {duration} {unit}...",
        "msg_tscan_waiting": "T-Scan: menunggu {duration} {unit}...",
        "msg_tscan_pulling": "T-Scan: menarik data hasil scan via 'f0'...",
        "msg_tscan_ok": "Time scan selesai: {n} titik data",
        "msg_error_start_gt_end": "Error: Start harus < End",
        "msg_csv_saved": "CSV disimpan: {path}",
        "msg_csv_error": "Gagal simpan CSV: {err}",
        "msg_csv_no_data": "Tidak ada data untuk diekspor",
        "msg_graph_saved": "Grafik disimpan: {path}",
        "msg_graph_error": "Gagal simpan grafik: {err}",
        "msg_graph_no_data": "Tidak ada grafik untuk diekspor",

        # -- Dialog --
        "dlg_csv_title": "Simpan CSV",
        "dlg_graph_title": "Simpan Grafik",

        # -- Printer --
        "grp_printer": "STATUS PRINTER",
        "lbl_printer_name": "Printer Default:",
        "status_printer_ready": "Ready",
        "status_printer_offline": "Offline/Error",
        "status_printer_none": "Tidak ada printer",
        "title_error": "Kesalahan",
        "title_info": "Informasi",
        "title_adv_conn": "Pengaturan Koneksi Lanjutan",
        "action_adv_conn": "Koneksi Lanjutan...",
        "status_searching": "Mencari alat otomatis...",
        "status_searching_no_ports": "Mencari alat... (Tidak ada port)",
        "status_searching_failed": "Pencarian otomatis gagal",
        "msg_auto_connecting": "Pencarian otomatis sedang berjalan, mohon tunggu...",
        "msg_err_not_connected": "Belum terhubung ke alat. Klik Connect terlebih dahulu.",
        "msg_err_conn_fail": "Tidak bisa membuka {port}. Periksa apakah port sudah benar dan tidak dipakai aplikasi lain.",
        "msg_err_no_response": "Tidak ada respons dari alat setelah percobaan. Periksa kabel, pastikan alat dalam mode PC Ctrl (tombol F4 di alat).",
        "msg_err_no_printer": "Tidak ada printer terdeteksi. Harap periksa koneksi printer.",
        "tt_refresh_printer": "Segarkan daftar printer",
        "btn_refresh_printer": "\u21ba",
        "msg_print_confirm": "Cetak ke printer {printer}?",
        "msg_print_ok": "Berhasil dikirim ke printer",
        "msg_print_error": "Gagal mencetak: {err}",
        "msg_print_skip": "Print dilewati",

        # -- Logging --
        "menu_open_log_folder": "Buka Folder Log",

        # -- Log detail --
        "log_ports_found": "COM ports ditemukan: {ports}",
        "log_no_ports": "(tidak ada)",
    },

    # ══════════════════════════════════════════════════════════════════════
    # ENGLISH
    # ══════════════════════════════════════════════════════════════════════
    "en": {
        # -- Window --
        "window_title": "Spektro-Control \u2014 UVmini-1240",

        # -- Menu bar --
        "menu_file": "File",
        "menu_instrument": "Instrument",
        "menu_tools": "Tools",
        "menu_export_csv": "Export CSV...",
        "menu_exit": "Exit",
        "menu_conn_info": "Connection Info",
        "menu_settings": "Settings...",

        # -- Toggle tema --
        "theme_to_dark": "\U0001f319  Dark Mode",
        "theme_to_light": "\u2600  Light Mode",

        # -- Toggle bahasa --
        "lang_to_en": "\U0001f310 English",
        "lang_to_id": "\U0001f310 Bahasa",

        # -- Panel: Serial Connection --
        "grp_connection": "SERIAL CONNECTION",
        "lbl_com_port": "COM Port:",
        "btn_connect": "Connect",
        "btn_disconnect": "Disconnect",
        "status_disconnected": "Disconnected",
        "status_connected": "Connected",

        # -- Panel: Measurement Mode --
        "grp_mode": "MEASUREMENT MODE",
        "lbl_mode": "Mode:",

        # -- Panel: GOTO Wavelength --
        "grp_goto_wl": "GOTO WAVELENGTH",
        "lbl_wavelength": "Wavelength (nm):",
        "btn_goto_wl": "GOTO WL",

        # -- Panel: Calibration --
        "grp_calibration": "CALIBRATION",
        "btn_auto_zero": "Auto Zero (A-Z)",
        "lbl_bl_start": "B-L Start (nm):",
        "lbl_bl_end": "B-L End (nm):",
        "btn_baseline": "Baseline (B-L)",

        # -- Panel: Read Data --
        "grp_read_data": "READ DATA",
        "btn_read_data": "Read Value (d)",

        # -- Panel: Wavelength Scan --
        "grp_wscan": "WAVELENGTH SCAN",
        "lbl_scan_start": "Start (nm):",
        "lbl_scan_end": "End (nm):",
        "lbl_speed": "Speed:",
        "btn_start_wscan": "\u25b6  Start Scan",
        "progress_scanning": "Scanning...",

        # -- Panel: Time Scan --
        "grp_tscan": "TIME SCAN",
        "lbl_duration": "Duration:",
        "lbl_unit": "Unit:",
        "unit_seconds": "Seconds",
        "unit_minutes": "Minutes",
        "btn_start_tscan": "\u25b6  Start Time Scan",
        "progress_measuring": "Measuring...",

        # -- Export --
        "btn_export_csv": "Export CSV",
        "btn_export_graph": "Export Graph",

        # -- Table --
        "header_wavelength": "Wavelength (nm)",
        "header_value": "Value",
        "header_time": "Time (s)",

        # -- Tabs --
        "tab_data": "Data",
        "tab_log": "Communication Log",

        # -- Log --
        "log_placeholder": "Serial communication log will appear here...",

        # -- Status bar / notifications --
        "msg_ready": "Ready \u2014 Select COM port and click Connect",
        "msg_connecting": "Connecting to {port}...",
        "msg_connected": "Connected to {port}",
        "msg_disconnected": "Disconnected",
        "msg_error_no_port": "Error: select a COM port first",
        "msg_connect_ok": "Connected to {port} \u2014 ENQ/ACK OK",
        "msg_connect_error": "Connect error: {err}",
        "msg_goto_wl_progress": "GOTO WL {wl} nm...",
        "msg_goto_wl_ok": "Wavelength set to {wl} nm",
        "msg_set_mode_progress": "Setting mode {label}...",
        "msg_set_mode_ok": "Mode set to {label}",
        "msg_auto_zero_progress": "A-Z (Auto Zero)...",
        "msg_auto_zero_ok": "Auto Zero complete",
        "msg_baseline_progress": "B-L (Baseline) {start}\u2013{end} nm...",
        "msg_baseline_ok": "Baseline correction complete ({start}\u2013{end} nm)",
        "msg_read_progress": "Reading data...",
        "msg_read_value": "Value: {val}",
        "msg_wscan_progress": "Wavelength Scan {start}\u2013{end} nm, speed {speed}...",
        "msg_wscan_waiting": "W-Scan: waiting for instrument to finish...",
        "msg_wscan_pulling": "W-Scan: pulling scan data via 'f0'...",
        "msg_wscan_ok": "Scan complete: {n} data points",
        "msg_tscan_progress": "Time Scan: {duration} {unit}...",
        "msg_tscan_waiting": "T-Scan: waiting {duration} {unit}...",
        "msg_tscan_pulling": "T-Scan: pulling scan data via 'f0'...",
        "msg_tscan_ok": "Time scan complete: {n} data points",
        "msg_error_start_gt_end": "Error: Start must be < End",
        "msg_csv_saved": "CSV saved: {path}",
        "msg_csv_error": "Failed to save CSV: {err}",
        "msg_csv_no_data": "No data to export",
        "msg_graph_saved": "Graph saved: {path}",
        "msg_graph_error": "Failed to save graph: {err}",
        "msg_graph_no_data": "No graph to export",

        # -- Dialogs --
        "dlg_csv_title": "Save CSV",
        "dlg_graph_title": "Save Graph",

        # -- Printer --
        "grp_printer": "PRINTER STATUS",
        "lbl_printer_name": "Default Printer:",
        "status_printer_ready": "Ready",
        "status_printer_offline": "Offline/Error",
        "status_printer_none": "No printer detected",
        "title_error": "Error",
        "title_info": "Information",
        "title_adv_conn": "Advanced Connection",
        "action_adv_conn": "Advanced Connection...",
        "status_searching": "Searching for instrument...",
        "status_searching_no_ports": "Searching... (No COM ports found)",
        "status_searching_failed": "Auto-connect failed",
        "msg_auto_connecting": "Auto-connect is running, please wait...",
        "msg_err_not_connected": "Not connected to device. Click Connect first.",
        "msg_err_conn_fail": "Cannot open {port}. Check if port is correct and not used by another application.",
        "msg_err_no_response": "No response from device after retries. Check cable, ensure device is in PC Ctrl mode (F4 key on device).",
        "msg_err_no_printer": "No printer detected. Please check printer connection.",
        "tt_refresh_printer": "Refresh printer list",
        "msg_print_confirm": "Print to {printer}?",
        "msg_print_ok": "Successfully sent to printer",
        "msg_print_error": "Failed to print: {err}",
        "msg_print_skip": "Print skipped",

        # -- Logging --
        "menu_open_log_folder": "Open Log Folder",

        # -- Log detail --
        "log_ports_found": "COM ports found: {ports}",
        "log_no_ports": "(none)",
    },
}

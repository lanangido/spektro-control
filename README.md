# Spektro-Control 🔬

**Spektro-Control** is a modern, cross-platform desktop application designed to interface with and control the **Shimadzu UVmini-1240** spectrophotometer.

Built as an open-source alternative to legacy proprietary software, Spektro-Control focuses on a **Plug-and-Play** experience, providing a responsive interface and an optimized workflow for laboratory analysis.

---

## 🚀 Key Features

*   **🔌 Smart Auto-Connect**: Say goodbye to manual COM port selection. The application silently scans all active USB/Serial ports in the background and automatically performs the ENQ/ACK handshake with the instrument. Just plug in the cable, and you're ready to go!
*   **🌍 Bilingual Support**: Full support for real-time language switching (English & Indonesian) without needing to restart the application.
*   **🎨 Modern Theming**: A beautifully designed interface with custom color palettes, fully supporting both Dark Mode (to reduce eye strain) and Light Mode.
*   **📊 Real-Time Analysis**:
    *   **Photometric Mode**: Read absorbance and transmittance at a specific wavelength.
    *   **Wavelength Scan**: Scan samples across a wavelength spectrum with live, high-framerate graph plotting.
    *   **Time Scan**: Monitor reaction kinetics or absorbance changes over time.
*   **📁 Data Management**: Export spectrum and kinetics readings to Spreadsheet format (`.csv`) or save high-resolution graphs directly as images (`.png`).
*   **🖨️ Direct Printing**: Native detection of system printers, allowing you to send instrument logs or graphs directly to physical printers.
*   **🛡️ Robust Error Handling**: Every serial interaction (data transmission, GOTO Wavelength, Auto-Zero/Baseline calibration) is protected by an elegant Alert System. This prevents the application from freezing or hanging when the instrument fails to respond.

---

## 💻 Tech Stack

Spektro-Control is developed entirely within the **Python** ecosystem, ensuring reliability and flexibility across operating systems (Windows, Linux, macOS).

*   **Language**: `Python 3.11+`
*   **GUI Framework**: `PySide6` (Official Qt6 binding for Python), utilized for the entire UI architecture and robust multithreading (QThread, QTimer).
*   **Data Visualization**: `pyqtgraph` (A fast, NumPy-based graphing library) for rendering live spectrum and kinetics graphs with high frame rates.
*   **Hardware Communication**: `pyserial` (Manages low-level RS-232 / COM port communication using Shimadzu's ENQ/ACK protocol).

### Repository Structure
*   `/ui/`: Contains the presentation logic (MainWindow, Dialogs, Themes) and language localization dictionaries (`strings.py`).
*   `/protocol/`: Contains the low-level serial communication implementation of the Shimadzu protocol (`uv_protocol.py`).
*   `main.py`: The main entry point of the application.
*   `requirements.txt`: Python dependency list.

---

## ⚙️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/username/spektro-control.git
    cd spektro-control
    ```

2.  **Create a Virtual Environment (Highly Recommended):**
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🏃 Usage Guide

Ensure your Shimadzu UVmini-1240 instrument is powered on, connected to your PC via an RS-232/USB-to-Serial cable, and set to **PC Ctrl** mode (usually by pressing the **F4** key on the instrument panel).

1.  Run the application from your terminal:
    ```bash
    python main.py
    ```
2.  The application will automatically scan, detect, and lock the connection with the instrument. You are now ready to analyze your samples!

*(If you ever need to configure the COM port manually, the setting is available in the menu bar under **Instrument > Advanced Connection...**)*

---
*Built to empower laboratory analysts — Happy Science!* 🧪

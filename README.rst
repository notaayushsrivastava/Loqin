===================================================
Loqin PC - Automated VIT Hostel Wi-Fi Client
===================================================

.. image:: assets/wizard_banner.bmp
   :width: 100%
   :alt: Loqin PC Banner

.. |installer| image:: https://img.shields.io/badge/Download-Loqin_Installer-0078D4?style=for-the-badge&logo=windows&logoColor=white
   :target: https://github.com/notaayushsrivastava/Loqin/releases/latest/download/Install_loqin.exe
   :alt: Download Loqin PC Installer

.. |vercel| image:: https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white
   :target: https://loqin-vit.vercel.app/
   :alt: Deployed on Vercel

.. |winget| image:: https://img.shields.io/winget/v/notaayushsrivastava.Loqin?logo=windows
   :target: https://winget.run/pkg/notaayushsrivastava.Loqin
   :alt: WinGet Version

|installer| |vercel| |winget|

.. image:: https://img.shields.io/badge/Python-3.8%2B-blue.svg
   :target: https://www.python.org/
.. image:: https://img.shields.io/badge/GUI-PyQt6-green.svg
   :target: https://pypi.org/project/PyQt6/
.. image:: https://img.shields.io/badge/Platform-Windows-lightgrey.svg
.. image:: https://img.shields.io/badge/Maintained%20by-Aayush%20Srivastava-orange.svg
   :target: https://aayushsrivastava.pythonanywhere.com/
.. image:: https://img.shields.io/badge/version-1.6.4-blue.svg
   :target: https://github.com/notaayushsrivastava/Loqin/releases
.. image:: https://img.shields.io/badge/License-GPLv3-blue.svg
   :target: LICENSE
   :alt: License: GPL v3

Connect once, forget forever. **Loqin PC** is a lightweight Windows system tray application designed to automatically authenticate and keep you connected to VIT hostel Wi-Fi.
Made for and by VITians.

.. contents:: Table of Contents
   :depth: 2
   :local:


Features
========

* **Automated Background Pinging:** Checks internet connection at regular intervals and logs back in immediately if disconnected.
* **Secure Credential Storage:** Employs OS-native credential management (Windows Credential Manager) via the ``keyring`` library.
* **System Tray Integration:** Runs discreetly near your system clock with right-click menu controls and status notifications.
* **Startup Launch:** Option to launch automatically whenever Windows boots up.
* **Easy Setup:** Prompts for your registration number and password directly inside the installation wizard.


How to Use (For Users)
======================

Step 1: Download & Install
--------------------------

1. Download the latest installer (``Install_Loqin.exe``) from the project releases.
2. Run the installer executable.
3. When prompted by the setup wizard, enter your **Registration Number / Username** and **Password**.
4. Check **Launch automatically on Windows startup** if you want the app to run on boot, then complete installation.

**OR**

1. Install using winget

   .. code-block:: bash

      winget install loqin

2. Proceed as the installer instructs.

Step 2: App Launch & System Tray
--------------------------------

Once opened, Loqin PC runs silently in the background.

* Look for the **Loqin padlock icon** in the Windows System Tray (bottom-right corner near the clock).
* When connected or re-authenticating, system notifications will toast briefly from the tray.

Step 3: System Tray Menu Options
--------------------------------

Right-click the Loqin icon in the system tray to open the quick action menu:

* **Status:** Shows current monitoring state.
* **Show Speed Graph:** Shows a graph monitoring download and upload speed.
* **Connect Now:** Manually forces an instant connection check and re-authentication attempt.
* **Pause/Resume Loqin:** Will temporarily stop the worker thread.
* **Performance Mode:** Will connect to the best BSSID on the network. (This may or may not change your network connectivity).
* **Account Details:** Shows account details with data transactions, and change password.
* **Configure Settings:** Opens the configuration window to update credentials, change check frequency (seconds), or toggle startup settings.
* **Exit Loqin:** Closes the application completely.

.. note::
   If your Wi-Fi session expires or disconnects, Loqin PC will automatically attempt to reconnect in the background without requiring you to open a browser portal.


Running from Source (For Developers)
====================================

Prerequisites
-------------

* Python 3.8 or higher
* Windows 10/11

Installation Steps
------------------

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/notaayushsrivastava/Loqin
      cd loqin

2. Create and activate a virtual environment:

   .. code-block:: bash

      python -m venv venv
      venv\Scripts\activate

3. Install required packages:

   .. code-block:: bash

      pip install -r requirements.txt

4. Run the app:

   .. code-block:: bash

      python app.py


Building the Executable
=======================

To package the application into a single standalone ``.exe`` file:

1. Ensure ``loqin_logo_small.png`` is present in the root folder.
2. Execute PyInstaller:

   .. code:: bash

      pyinstaller --noconsole --onefile --add-data "assets;assets" --icon="assets/loqin_logo_small.png" --version-file="version_info.txt" --name="Loqin" --clean app.py

3. The output executable will be placed in the ``dist/`` directory.


Building the Installer Package
==============================

To compile the setup wizard with custom credential prompting:

1. Download and install `Inno Setup <https://jrsoftware.org/isdl.php>`_.
2. Open ``latch_installer_script.iss`` in Inno Setup.
3. Click **Compile** (or press ``Ctrl + F9``).
4. Find the finished installer inside the ``Output/`` folder.


License
=======

Copyright (c) 2026 Aayush Srivastava. All rights reserved.

This source code is licensed under the GPLv3 License found in the LICENSE file in the root directory of this source tree.

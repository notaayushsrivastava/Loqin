import sys
import pytest

import app as loqin_app


def test_platform_conditional_attributes():
    if sys.platform == "win32":
        assert loqin_app.winreg is not None
        assert loqin_app.pywifi is not None
    else:
        assert loqin_app.winreg is None
        assert loqin_app.pywifi is None
        assert loqin_app.const is None


def test_non_windows_guards():
    # Calling auto-start helpers should be safe regardless of platform
    assert loqin_app.set_auto_start(False) is None
    if sys.platform != "win32":
        assert loqin_app.is_auto_start_enabled() is False
        assert loqin_app.ensure_single_instance() is None


def test_thread_fallbacks_when_pywifi_absent():
    # If pywifi is None, worker threads should cleanly emit errors without crashing
    scan_thread = loqin_app.WiFiScanThread()
    errors = []
    scan_thread.scan_failed.connect(lambda err: errors.append(err))
    
    saved_pywifi = loqin_app.pywifi
    try:
        loqin_app.pywifi = None
        scan_thread.run()
        assert len(errors) == 1
        assert "Windows" in errors[0]
    finally:
        loqin_app.pywifi = saved_pywifi

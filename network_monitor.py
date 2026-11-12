"""
Loqin Network Event Monitor

Provides OS-native network event monitoring for Windows (Native Wi-Fi + Network List Manager)
and macOS (CoreWLAN), triggering reactive connection/disconnection checks while eliminating
aggressive polling.
"""

from __future__ import annotations

import sys
import threading
import logging
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger("loqin.network_monitor")


class BaseNetworkEventMonitor(QObject):
    """
    Abstract base class for OS network event monitors.
    Emits Qt signals so the UI/check thread can react on the main event loop.
    """
    # Emits event type: 'connected', 'disconnected', 'connectivity_changed'
    network_changed = pyqtSignal(str)
    monitor_error = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._is_running = False

    def start(self) -> None:
        """Start listening to OS network events."""
        raise NotImplementedError

    def stop(self) -> None:
        """Stop listening and cleanly release native handles/callbacks."""
        raise NotImplementedError

    def is_running(self) -> bool:
        return self._is_running


# ============================================================================
# Windows Native Wi-Fi (wlanapi.dll) & Network List Manager (NLM) Monitor
# ============================================================================

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    # Wi-Fi Notification Source & ACM Code Definitions
    WLAN_NOTIFICATION_SOURCE_NONE = 0
    WLAN_NOTIFICATION_SOURCE_ACM = 0x00000008
    WLAN_NOTIFICATION_SOURCE_MSM = 0x00000010

    # WLAN_NOTIFICATION_ACM enum
    WLAN_ACM_CONNECTION_START = 10
    WLAN_ACM_CONNECTION_COMPLETE = 11
    WLAN_ACM_CONNECTION_ATTEMPT_FAIL = 12
    WLAN_ACM_INTERFACE_ARRIVAL = 14
    WLAN_ACM_INTERFACE_REMOVAL = 15
    WLAN_ACM_NETWORK_NOT_AVAILABLE = 19
    WLAN_ACM_NETWORK_AVAILABLE = 20
    WLAN_ACM_DISCONNECTING = 21
    WLAN_ACM_DISCONNECTED = 22

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

    class WLAN_NOTIFICATION_DATA(ctypes.Structure):
        _fields_ = [
            ("NotificationSource", wintypes.DWORD),
            ("NotificationCode", wintypes.DWORD),
            ("InterfaceGuid", GUID),
            ("dwDataSize", wintypes.DWORD),
            ("pData", ctypes.c_void_p),
        ]

    WLAN_NOTIFICATION_CALLBACK = ctypes.WINFUNCTYPE(
        None,
        ctypes.POINTER(WLAN_NOTIFICATION_DATA),
        ctypes.c_void_p,
    )

    class WindowsNetworkEventMonitor(BaseNetworkEventMonitor):
        """
        Hybrid Windows monitor using:
        1. Native Wi-Fi API (wlanapi.dll) for immediate link/association events.
        2. Network List Manager (NLM) COM events for system-level internet connectivity transitions.
        """

        def __init__(self, parent: Optional[QObject] = None) -> None:
            super().__init__(parent)
            self._wlan_handle = None
            self._c_callback = None
            self._nlm_thread: Optional[threading.Thread] = None
            self._nlm_running = False
            self._lock = threading.Lock()

        def start(self) -> None:
            with self._lock:
                if self._is_running:
                    return
                self._is_running = True

            errors = []

            # 1. Start Native Wi-Fi Notifications
            try:
                self._start_wlan_notifications()
            except Exception as e:
                err_msg = f"Failed to initialize Windows Native Wi-Fi monitor: {e}"
                logger.warning(err_msg)
                errors.append(err_msg)

            # 2. Start Network List Manager COM event listener
            try:
                self._start_nlm_listener()
            except Exception as e:
                err_msg = f"Failed to initialize Windows NLM monitor: {e}"
                logger.warning(err_msg)
                errors.append(err_msg)

            if errors and not self._wlan_handle and not self._nlm_thread:
                self._is_running = False
                self.monitor_error.emit("; ".join(errors))

        def _start_wlan_notifications(self) -> None:
            wlan = ctypes.windll.wlanapi
            handle = wintypes.HANDLE()
            negotiated_version = wintypes.DWORD()

            ret = wlan.WlanOpenHandle(2, None, ctypes.byref(negotiated_version), ctypes.byref(handle))
            if ret != 0:
                raise RuntimeError(f"WlanOpenHandle failed with error code {ret}")

            self._wlan_handle = handle

            def _wlan_callback(data_ptr, context):
                try:
                    if not data_ptr or not self._is_running:
                        return
                    data = data_ptr.contents
                    if data.NotificationSource == WLAN_NOTIFICATION_SOURCE_ACM:
                        code = data.NotificationCode
                        if code in (WLAN_ACM_CONNECTION_COMPLETE, WLAN_ACM_NETWORK_AVAILABLE):
                            self.network_changed.emit("connected")
                        elif code in (WLAN_ACM_DISCONNECTED, WLAN_ACM_INTERFACE_REMOVAL, WLAN_ACM_NETWORK_NOT_AVAILABLE):
                            self.network_changed.emit("disconnected")
                        elif code == WLAN_ACM_INTERFACE_ARRIVAL:
                            self.network_changed.emit("connectivity_changed")
                except Exception as ex:
                    logger.debug(f"Exception inside WLAN callback: {ex}")

            # Keep a strong reference to the callback to prevent garbage collection
            self._c_callback = WLAN_NOTIFICATION_CALLBACK(_wlan_callback)
            prev_source = wintypes.DWORD()

            ret = wlan.WlanRegisterNotification(
                self._wlan_handle,
                WLAN_NOTIFICATION_SOURCE_ACM,
                True,
                self._c_callback,
                None,
                None,
                ctypes.byref(prev_source),
            )
            if ret != 0:
                wlan.WlanCloseHandle(self._wlan_handle, None)
                self._wlan_handle = None
                self._c_callback = None
                raise RuntimeError(f"WlanRegisterNotification failed with error code {ret}")

        def _start_nlm_listener(self) -> None:
            self._nlm_running = True
            self._nlm_thread = threading.Thread(
                target=self._nlm_worker,
                name="LoqinNLMThread",
                daemon=True,
            )
            self._nlm_thread.start()

        def _nlm_worker(self) -> None:
            try:
                import comtypes
                import comtypes.client

                ctypes.windll.ole32.CoInitialize(None)
            except Exception as e:
                logger.debug(f"CoInitialize error in NLM worker: {e}")
                return

            advise = None
            nlm = None
            try:
                # CLSID for NetworkListManager: {DCB00C01-570F-4A9B-8D69-199FDBA5723B}
                nlm = comtypes.client.CreateObject("{DCB00C01-570F-4A9B-8D69-199FDBA5723B}")

                monitor = self

                class NLMEvents:
                    def ConnectivityChanged(self, this, new_connectivity):
                        if not monitor._is_running:
                            return
                        # NLM_CONNECTIVITY values:
                        # 0 = Disconnected
                        # 0x40 / 0x400 = IPv4 / IPv6 Internet
                        # 0x10 / 0x20 = IPv4 Subnet / Local Network (portal)
                        if new_connectivity == 0:
                            monitor.network_changed.emit("disconnected")
                        elif new_connectivity & 0x440:  # Internet
                            monitor.network_changed.emit("connected")
                        else:  # Local network / captive portal
                            monitor.network_changed.emit("connectivity_changed")

                advise = comtypes.client.GetEvents(nlm, NLMEvents())

                msg = wintypes.MSG()
                while self._nlm_running and self._is_running:
                    # Wait up to 500ms or wake when COM messages arrive
                    ctypes.windll.user32.MsgWaitForMultipleObjectsEx(0, None, 500, 0x04FF, 0)
                    while ctypes.windll.user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):
                        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

            except Exception as e:
                logger.debug(f"NLM worker loop ended or failed: {e}")
            finally:
                if advise is not None:
                    try:
                        del advise
                    except Exception:
                        pass
                if nlm is not None:
                    try:
                        del nlm
                    except Exception:
                        pass
                try:
                    ctypes.windll.ole32.CoUninitialize()
                except Exception:
                    pass

        def stop(self) -> None:
            with self._lock:
                if not self._is_running:
                    return
                self._is_running = False

            # Stop NLM thread
            self._nlm_running = False
            if self._nlm_thread and self._nlm_thread.is_alive():
                self._nlm_thread.join(timeout=1.0)
                self._nlm_thread = None

            # Stop WLAN notification
            if self._wlan_handle:
                try:
                    wlan = ctypes.windll.wlanapi
                    prev_source = wintypes.DWORD()
                    wlan.WlanRegisterNotification(
                        self._wlan_handle,
                        WLAN_NOTIFICATION_SOURCE_NONE,
                        True,
                        None,
                        None,
                        None,
                        ctypes.byref(prev_source),
                    )
                    wlan.WlanCloseHandle(self._wlan_handle, None)
                except Exception as e:
                    logger.debug(f"Error unregistering WLAN notifications: {e}")
                finally:
                    self._wlan_handle = None
                    self._c_callback = None


# ============================================================================
# macOS CoreWLAN Event Monitor
# ============================================================================

class MacNetworkEventMonitor(BaseNetworkEventMonitor):
    """
    macOS event monitor using CoreWLAN framework delegates to detect link,
    power, and SSID changes.
    """

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._delegate = None
        self._client = None

    def start(self) -> None:
        if self._is_running:
            return
        self._is_running = True

        try:
            import objc
            from CoreWLAN import (
                CWWiFiClient,
                CWEventTypeLinkDidChange,
                CWEventTypePowerDidChange,
                CWEventTypeSSIDDidChange,
                CWEventTypeBSSIDDidChange,
            )
            from Foundation import NSObject

            monitor = self

            class CWEventDelegate(NSObject):
                def linkDidChangeForWiFiInterfaceWithName_(self, interface_name):
                    if not monitor._is_running:
                        return
                    try:
                        client = CWWiFiClient.sharedWiFiClient()
                        iface = client.interfaceWithName_(interface_name) or client.interface()
                        if iface and iface.powerOn():
                            ssid = iface.ssid()
                            if ssid:
                                monitor.network_changed.emit("connected")
                            else:
                                monitor.network_changed.emit("disconnected")
                        else:
                            monitor.network_changed.emit("disconnected")
                    except Exception as ex:
                        logger.debug(f"CoreWLAN link changed error: {ex}")
                        monitor.network_changed.emit("connectivity_changed")

                def ssidDidChangeForWiFiInterfaceWithName_(self, interface_name):
                    if not monitor._is_running:
                        return
                    monitor.network_changed.emit("connected")

                def powerStateDidChangeForWiFiInterfaceWithName_(self, interface_name):
                    if not monitor._is_running:
                        return
                    try:
                        client = CWWiFiClient.sharedWiFiClient()
                        iface = client.interfaceWithName_(interface_name) or client.interface()
                        if iface and iface.powerOn():
                            monitor.network_changed.emit("connectivity_changed")
                        else:
                            monitor.network_changed.emit("disconnected")
                    except Exception:
                        monitor.network_changed.emit("disconnected")

                def bssidDidChangeForWiFiInterfaceWithName_(self, interface_name):
                    if not monitor._is_running:
                        return
                    monitor.network_changed.emit("connectivity_changed")

            self._client = CWWiFiClient.sharedWiFiClient()
            self._delegate = CWEventDelegate.alloc().init()
            self._client.setDelegate_(self._delegate)

            # Start monitoring events
            for event_type in (
                CWEventTypeLinkDidChange,
                CWEventTypePowerDidChange,
                CWEventTypeSSIDDidChange,
                CWEventTypeBSSIDDidChange,
            ):
                err = None
                self._client.startMonitoringEventWithType_error_(event_type, None)

        except Exception as e:
            self._is_running = False
            err_msg = f"Failed to initialize macOS CoreWLAN monitor: {e}"
            logger.warning(err_msg)
            self.monitor_error.emit(err_msg)

    def stop(self) -> None:
        if not self._is_running:
            return
        self._is_running = False

        if self._client and self._delegate:
            try:
                from CoreWLAN import (
                    CWEventTypeLinkDidChange,
                    CWEventTypePowerDidChange,
                    CWEventTypeSSIDDidChange,
                    CWEventTypeBSSIDDidChange,
                )
                for event_type in (
                    CWEventTypeLinkDidChange,
                    CWEventTypePowerDidChange,
                    CWEventTypeSSIDDidChange,
                    CWEventTypeBSSIDDidChange,
                ):
                    try:
                        self._client.stopMonitoringEventWithType_error_(event_type, None)
                    except Exception:
                        pass
                self._client.setDelegate_(None)
            except Exception as e:
                logger.debug(f"Error stopping CoreWLAN monitor: {e}")
            finally:
                self._delegate = None
                self._client = None


# ============================================================================
# Fallback Monitor (for unsupported platforms or when native registration fails)
# ============================================================================

class FallbackNetworkEventMonitor(BaseNetworkEventMonitor):
    """
    Fallback monitor when native OS APIs are unavailable.
    Does not emit OS events, ensuring the app seamlessly relies on the fallback timer.
    """

    def start(self) -> None:
        self._is_running = True
        self.monitor_error.emit("Native network event monitoring unavailable; running in fallback polling mode.")

    def stop(self) -> None:
        self._is_running = False


# ============================================================================
# Factory Function
# ============================================================================

def get_network_event_monitor(parent: Optional[QObject] = None) -> BaseNetworkEventMonitor:
    """Returns the platform-appropriate NetworkEventMonitor."""
    if sys.platform == "win32":
        return WindowsNetworkEventMonitor(parent)
    elif sys.platform == "darwin":
        return MacNetworkEventMonitor(parent)
    else:
        return FallbackNetworkEventMonitor(parent)

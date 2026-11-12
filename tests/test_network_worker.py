from unittest.mock import patch, MagicMock
import requests
import pytest

from app import NetworkWorker


def test_extract_account_url_patterns():
    # 1. IP with session ID
    html_1 = '<html><a href="http://10.10.10.1/cgi-bin/registration/Main.jsp?sessionId=abc123xyz">Details</a></html>'
    url_1 = NetworkWorker.extract_account_url(html_1)
    assert url_1 == "http://10.10.10.1/cgi-bin/registration/Main.jsp?sessionId=abc123xyz"

    # 2. Hostname/Direct URL
    html_2 = 'window.location = "http://phc.prontonetworks.com/registration/Main.jsp?sessionId=sess_999";'
    url_2 = NetworkWorker.extract_account_url(html_2)
    assert url_2 == "http://phc.prontonetworks.com/registration/Main.jsp?sessionId=sess_999"

    # 3. Empty or unmatching HTML
    assert NetworkWorker.extract_account_url("") == ""
    assert NetworkWorker.extract_account_url("<html><body>No links here</body></html>") == ""


def test_check_network_state():
    worker = NetworkWorker({"username": "user", "interval": 30})

    # Test ONLINE (status code 204)
    mock_res_204 = MagicMock()
    mock_res_204.status_code = 204
    with patch("requests.get", return_value=mock_res_204):
        assert worker.check_network_state() == "ONLINE"

    # Test PORTAL (status code 302 or 200)
    mock_res_302 = MagicMock()
    mock_res_302.status_code = 302
    with patch("requests.get", return_value=mock_res_302):
        assert worker.check_network_state() == "PORTAL"

    # Test OFFLINE (RequestException)
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Offline")):
        assert worker.check_network_state() == "OFFLINE"

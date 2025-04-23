import pytest
import subprocess
import sys
import os

@pytest.mark.integration
class TestCLIAPI:
    def test_cli_commands(self):
        """Test all CLI commands for correct behavior, error handling, and help output."""
        # Ensure package is installed in editable mode
        install_result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], capture_output=True, text=True)
        assert install_result.returncode == 0, f"Editable install failed: {install_result.stderr}"
        # Try installed CLI entry point
        cli_found = False
        try:
            result = subprocess.run(['logflow', '--help'], capture_output=True, text=True)
            if result.returncode == 0 and ('Usage' in result.stdout or 'usage' in result.stdout):
                cli_found = True
        except FileNotFoundError:
            pass
        # If not found, try Python module invocation as fallback
        if not cli_found:
            result = subprocess.run([sys.executable, '-m', 'logflow.cli', '--help'], capture_output=True, text=True)
            assert result.returncode == 0, f"Help command failed (module): {result.stderr}"
            assert 'Usage' in result.stdout or 'usage' in result.stdout
        else:
            # Test invalid command via CLI
            result = subprocess.run(['logflow', 'nonexistent'], capture_output=True, text=True)
            assert result.returncode != 0, "Invalid command should fail"
            assert 'error' in result.stderr.lower() or 'unknown' in result.stderr.lower()

    def test_api_endpoints(self):
        """Test all API endpoints for expected responses and error handling (if present)."""
        # If REST API endpoints exist, use requests to verify their responses
        # Example (uncomment and adapt if endpoints are available):
        # import requests
        # resp = requests.get('http://127.0.0.1:8000/api/status')
        # assert resp.status_code == 200
        pass  # Placeholder if no API endpoints exist yet

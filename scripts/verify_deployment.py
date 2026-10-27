import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable


NAMESPACE = os.environ["KUBE_NAMESPACE"]
RELEASE = os.environ["HELM_RELEASE"]
HealthCheck = tuple[str, int, Callable[[bytes], bool]]


def local_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def verify_service(
    service: str,
    remote_port: int,
    checks: list[HealthCheck],
) -> None:
    port = local_port()
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(
            [
                "kubectl",
                "port-forward",
                "--address=127.0.0.1",
                "--namespace",
                NAMESPACE,
                f"service/{service}",
                f"{port}:{remote_port}",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            for path, expected_status, validator in checks:
                url = f"http://127.0.0.1:{port}{path}"
                deadline = time.monotonic() + 90
                while True:
                    if process.poll() is not None:
                        log.seek(0)
                        details = log.read().decode(errors="replace").strip()
                        raise RuntimeError(
                            f"kubectl port-forward for {service} exited: {details}"
                        )
                    try:
                        status, body = request(url)
                    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
                        if time.monotonic() >= deadline:
                            raise RuntimeError(f"Health request timed out: {url}")
                        time.sleep(2)
                        continue
                    if status != expected_status or not validator(body):
                        raise RuntimeError(
                            f"Unexpected response from {url}: HTTP {status}"
                        )
                    print(f"Verified {service}{path}: HTTP {status}")
                    break
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def main() -> None:
    verify_service(
        f"{RELEASE}-backend",
        8080,
        [
            (
                "/support/actuator/health",
                200,
                lambda body: json.loads(body).get("status") == "UP",
            )
        ],
    )
    verify_service(
        f"{RELEASE}-frontend",
        80,
        [
            ("/support/", 200, lambda body: b"<html" in body.lower()),
            ("/support/api/auth/me", 401, bool),
        ],
    )


if __name__ == "__main__":
    main()

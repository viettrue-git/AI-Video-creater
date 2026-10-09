"""Minimal ComfyUI HTTP API client (stdlib only).

Covers what the pipeline needs: upload a reference image, queue an API-format
workflow, wait for it to finish, and download the produced images.
"""
import json
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

DEFAULT_SERVER = "http://127.0.0.1:8188"


class ComfyUIError(RuntimeError):
    pass


class ComfyUIClient:
    def __init__(self, server=DEFAULT_SERVER, timeout=30):
        self.server = server.rstrip("/")
        self.timeout = timeout
        self.client_id = str(uuid.uuid4())

    def _request(self, path, data=None, headers=None):
        req = urllib.request.Request(self.server + path, data=data, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            raise ComfyUIError(f"{path} -> HTTP {e.code}: {e.read().decode('utf-8', 'replace')}") from e
        except urllib.error.URLError as e:
            raise ComfyUIError(f"Cannot reach ComfyUI at {self.server}: {e.reason}") from e

    def _get_json(self, path):
        return json.loads(self._request(path))

    def is_alive(self):
        try:
            self._get_json("/system_stats")
            return True
        except ComfyUIError:
            return False

    def upload_image(self, file_path, overwrite=True):
        """Upload a local image into ComfyUI's input folder; returns the stored name."""
        file_path = Path(file_path)
        boundary = uuid.uuid4().hex
        mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        parts = [
            f'--{boundary}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\n{str(overwrite).lower()}\r\n'.encode(),
            (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{file_path.name}"\r\n'
             f"Content-Type: {mime}\r\n\r\n").encode() + file_path.read_bytes() + b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
        body = b"".join(parts)
        resp = self._request("/upload/image", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
        info = json.loads(resp)
        return f"{info['subfolder']}/{info['name']}" if info.get("subfolder") else info["name"]

    def queue_prompt(self, workflow):
        body = json.dumps({"prompt": workflow, "client_id": self.client_id}).encode()
        resp = json.loads(self._request("/prompt", body, {"Content-Type": "application/json"}))
        # HTTP 200 may still carry node_errors for partial outputs; only a missing prompt_id means rejected
        if not resp.get("prompt_id"):
            raise ComfyUIError(f"Workflow rejected: {json.dumps(resp.get('node_errors', resp))[:1000]}")
        return resp["prompt_id"]

    def wait_for_result(self, prompt_id, poll_seconds=2.0, max_wait_seconds=3600):
        """Poll /history until the prompt finishes; returns its history entry."""
        deadline = time.time() + max_wait_seconds
        while time.time() < deadline:
            history = self._get_json(f"/history/{prompt_id}")
            entry = history.get(prompt_id)
            if entry:
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    raise ComfyUIError(f"Prompt {prompt_id} failed: {json.dumps(status.get('messages'))[:1500]}")
                if status.get("completed", True):
                    return entry
            time.sleep(poll_seconds)
        raise ComfyUIError(f"Timed out waiting for prompt {prompt_id}")

    @staticmethod
    def execution_seconds(history_entry):
        """Pure execution time (excludes queue wait) from execution_start/success timestamps, or None."""
        stamps = {kind: data.get("timestamp") for kind, data in history_entry.get("status", {}).get("messages", [])}
        start, end = stamps.get("execution_start"), stamps.get("execution_success")
        return round((end - start) / 1000, 1) if start and end else None

    def download_images(self, history_entry, dest_paths):
        """Save every output image of a finished prompt; dest_paths is a list consumed in order."""
        saved = []
        for node_output in history_entry.get("outputs", {}).values():
            # images/videos come under "images", SaveAudio results under "audio"
            for img in node_output.get("images", []) + node_output.get("audio", []):
                if img.get("type") != "output" or len(saved) >= len(dest_paths):
                    continue
                query = urllib.parse.urlencode({k: img[k] for k in ("filename", "subfolder", "type")})
                dest = Path(dest_paths[len(saved)])
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(self._request(f"/view?{query}"))
                saved.append(dest)
        return saved

    def free_memory(self):
        """Ask ComfyUI to unload models and free VRAM (e.g. before running a local LLM)."""
        body = json.dumps({"unload_models": True, "free_memory": True}).encode()
        self._request("/free", body, {"Content-Type": "application/json"})

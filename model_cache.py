"""Makes sure a Hugging Face model is in the local cache BEFORE it is loaded, and reports download progress.

Why this exists: when the first question triggered a silent 3 GB download inside the Streamlit script, the page showed
"Starting the chatbot..." with no sign of progress, and any network problem looked like an endless wait. Here the
cache is checked first (no network needed when the model is already there), a download shows real byte counts, and a
failure becomes a short readable error."""
import os


def _fmt(n):
    return f"{n / 1e6:.0f} MB" if n < 1e9 else f"{n / 1e9:.2f} GB"


def ensure_model_files(repo_id: str, progress=None, offline=False):
    """Return a local path (or the repo id) that from_pretrained can load. Raises RuntimeError with a clear message."""
    if os.path.isdir(repo_id):                                      # a local folder: nothing to download
        return repo_id
    from huggingface_hub import snapshot_download
    try:                                                            # 1) already cached? then no network is used
        return snapshot_download(repo_id, local_files_only=True)
    except Exception:
        pass
    if offline:
        raise RuntimeError(f"The model '{repo_id}' is not in the local cache and JRU_OFFLINE=1 is set. "
                           "Run 'python prepare.py' once while online.")
    if progress:
        progress(f"Downloading {repo_id} (first run only, this can take several minutes)...")
    try:
        from tqdm.auto import tqdm

        class _Bar(tqdm):
            """Reports total bytes downloaded across files to the progress callback, at most once per second."""
            _last = 0.0
            _done = 0
            _total = 0

            def __init__(self, *a, **kw):
                kw["disable"] = True                                # no console bars, we report ourselves
                super().__init__(*a, **kw)
                self._is_bytes = kw.get("unit") == "B"
                if self._is_bytes and kw.get("total"):
                    _Bar._total += int(kw["total"])

            def update(self, n=1):
                import time
                if getattr(self, "_is_bytes", False):
                    _Bar._done += int(n or 0)
                    now = time.time()
                    if progress and now - _Bar._last > 1.0 and _Bar._total:
                        _Bar._last = now
                        progress(f"Downloading {repo_id}: {_fmt(_Bar._done)} of {_fmt(_Bar._total)}")
                return super().update(n)

        return snapshot_download(repo_id, tqdm_class=_Bar)
    except TypeError:                                               # older huggingface_hub without tqdm_class
        return snapshot_download(repo_id)
    except Exception as exc:
        raise RuntimeError(f"Could not download '{repo_id}' ({type(exc).__name__}). Check the internet connection, "
                           "or run 'python prepare.py' once on a connection that can reach huggingface.co.") from exc

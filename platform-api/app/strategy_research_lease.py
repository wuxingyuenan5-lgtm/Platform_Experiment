"""Process lifetime lease for the existing Platform research worker."""

import os
from pathlib import Path


class ResearchLease:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        self.file = (root / "consumer.lock").open("a+b")
        try:
            if os.name == "nt":
                import msvcrt

                self.file.seek(0)
                if self.file.read(1) == b"":
                    self.file.write(b"0")
                    self.file.flush()
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError("research consumer already active") from None

    def close(self):
        self.file.close()

"""Apply process limits before exec, without unsafe preexec_fn in a threaded server."""
from __future__ import annotations

import json
import os
import resource
import sys


def main():
    cfg = json.loads(sys.argv[1])
    for kind, ceiling in [(resource.RLIMIT_CPU, cfg["worker_cpu_seconds"]),
                          (resource.RLIMIT_AS, cfg["worker_address_space_bytes"]),
                          (resource.RLIMIT_FSIZE, cfg["worker_log_bytes"]),
                          (resource.RLIMIT_NOFILE, 128)]:
        resource.setrlimit(kind, (ceiling, ceiling))
    os.execve(sys.argv[2], sys.argv[2:], os.environ)


if __name__ == "__main__":
    main()

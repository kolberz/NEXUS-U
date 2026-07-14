from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    image = os.environ["IMAGE_REF"]
    source = Path(os.environ.get("K8S_TEMPLATE", "deploy/k8s/deployment.yaml"))
    target = Path(os.environ.get("K8S_OUTPUT", "deploy/k8s/rendered.yaml"))
    text = source.read_text().replace("ghcr.io/OWNER/nexus-u:1.0.0", image)
    target.write_text(text)
    print(target)


if __name__ == "__main__":
    main()

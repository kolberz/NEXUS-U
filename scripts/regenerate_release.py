from pathlib import Path
from nexus_u.benchmark import write_benchmark

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = write_benchmark(root / "benchmark-results", root)
    print(result["summary"])

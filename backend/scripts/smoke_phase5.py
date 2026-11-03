"""Chronos 1.0 — HTTP real isolado: cenários, financeiro e sensibilidade."""
import argparse
from smoke_phase3 import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True)
    main(parser.parse_args().runtime, phase=5)

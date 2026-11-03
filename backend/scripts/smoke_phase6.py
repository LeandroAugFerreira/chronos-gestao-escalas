from pathlib import Path
import argparse
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke_phase3 import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chronos 1.0 — integração HTTP isolada da Fase 6")
    parser.add_argument("--runtime", required=True)
    main(parser.parse_args().runtime, phase=6)

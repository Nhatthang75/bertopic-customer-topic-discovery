"""Demo script to run the BERTopic Customer Conversation PoC Dashboard."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bertopic_poc.io import ROOT
from bertopic_poc.dashboard import load_dashboard_state, render_terminal_dashboard


def main():
    print("Loading pre-computed Schema 1.0.0 artifacts (no models fitted)...")
    state = load_dashboard_state(ROOT / 'artifacts/phase1')
    rendered = render_terminal_dashboard(state)
    print("\n" + rendered)


if __name__ == '__main__':
    main()

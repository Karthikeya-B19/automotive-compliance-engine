"""Export the versioned synthetic advisory corpus for inspection and retrieval."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.rag.automotive_retrieval import CARD_PATH, default_cards
if __name__ == '__main__':
    CARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    CARD_PATH.write_text(json.dumps(default_cards(), indent=2), encoding='utf-8')
    print(f'Exported {len(default_cards())} synthetic rule cards: {CARD_PATH}')

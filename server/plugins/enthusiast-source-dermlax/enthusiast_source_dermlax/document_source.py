import csv
from pathlib import Path
from typing import Any
import re
import hashlib

from enthusiast_common import DocumentDetails, DocumentSourcePlugin


class DermlaxDocumentSource(DocumentSourcePlugin):
    def __init__(self, data_set_id: Any):
        super().__init__(data_set_id)
        self.sample_file_path = Path(__file__).parent / "dermlax_documents.csv"

    def fetch(self) -> list[DocumentDetails]:
        results = []
        with open(self.sample_file_path, newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                results.append(DocumentDetails(url=row["URL"], title=row["Title"], content=row["Content"]))

        return results


# -------------------------------
# Standalone debugging utilities
# -------------------------------

def _slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s or "untitled"


def _fallback_url(data_set_id: Any, title: str) -> str:
    slug = _slugify(title)
    h = hashlib.sha256((title or "").encode("utf-8")).hexdigest()[:8]
    return f"ds/{data_set_id}/doc/{slug}-{h}"


def main() -> None:
    """Quick, standalone validator for the Dermlax CSV.

    Prints a summary and highlights rows that would break sync (e.g., missing URL).
    Run with: `python document_source.py`
    """
    try:
        src = DermlaxDocumentSource(data_set_id="debug")
        path = src.sample_file_path
        if not path.exists():
            print(f"❌ CSV not found at: {path}")
            return

        import csv
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = list(csv.DictReader(fh))

        total = len(reader)
        bad_url = []
        bad_title = []
        bad_content = []

        for idx, row in enumerate(reader, start=1):
            url = (row.get("URL") or "").strip()
            title = (row.get("Title") or "").strip()
            content = (row.get("Content") or "").strip()

            if not url:
                # Suggest a stable fallback so you can fix the CSV or update the plugin
                suggestion = _fallback_url(src.data_set_id, title or f"row-{idx}")
                bad_url.append((idx, title, suggestion))
            if not title:
                bad_title.append(idx)
            if content == "":
                bad_content.append(idx)

        print("\n===== Dermlax Document CSV Check =====")
        print(f"File: {path}")
        print(f"Total rows: {total}")
        print(f"Missing URL: {len(bad_url)} | Missing Title: {len(bad_title)} | Empty Content: {len(bad_content)}")

        if bad_url:
            print("\nRows with missing URL (showing up to 10):")
            for i, (rownum, title, suggestion) in enumerate(bad_url[:10], start=1):
                print(f"  {i:>2}. row #{rownum}: title=\"{title}\" → suggested_fallback_url=\"{suggestion}\"")

        if total and not bad_url:
            # Demonstrate the plugin fetch works end-to-end when URLs exist
            try:
                docs = src.fetch()
                print(f"\n✅ fetch() would emit {len(docs)} DocumentDetails items.")
                for i, d in enumerate(docs[:3], start=1):
                    print(f"  [{i}] url={d.url} | title={d.title} | content_len={len(d.content or '')}")
            except Exception as e:
                print(f"\n⚠️ fetch() raised an exception: {e}")

        print("\nTip: If your source lacks real URLs, either (a) fill URL in the CSV, or (b) update fetch() to synthesize a fallback with the pattern above.")
    except Exception as ex:
        print(f"Unexpected error during debug run: {ex}")


if __name__ == "__main__":
    main()

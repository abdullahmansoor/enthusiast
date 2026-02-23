import csv
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, List

from enthusiast_common import ProductDetails, ProductSourcePlugin


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return re.sub(r"\s+", " ", "".join(self._parts)).strip()


def _strip_html(text: str) -> str:
    """Strip HTML tags and decode common entities from WooCommerce field values."""
    if not text:
        return ""
    s = _HTMLStripper()
    try:
        s.feed(text)
        result = s.get_text()
    except Exception:
        result = re.sub(r"<[^>]+>", " ", text)
    # Decode leftover escaped newlines
    result = result.replace("\\n", " ")
    return re.sub(r"\s+", " ", result).strip()


def _safe_price(raw: str) -> str | None:
    raw = (raw or "").strip().replace("$", "").replace(",", "")
    try:
        val = float(raw)
        return str(val) if val > 0 else None
    except ValueError:
        return None


class CustomProductSource(ProductSourcePlugin):
    """
    WooCommerce product export source for FindGolf / Pinter Industries.

    Reads the CSV exported from WooCommerce and indexes:
      - simple products
      - variation products (e.g. BallBoon Silver/Red/Gold)
    Skips 'variable' parent rows (they carry no price themselves).
    """

    CSV_FILENAME = "products.csv"

    def __init__(self, data_set_id: Any):
        super().__init__(data_set_id)
        self.csv_path = Path(__file__).with_name(self.CSV_FILENAME)

    def fetch(self) -> List[ProductDetails]:
        products = []
        with open(self.csv_path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                product_type = (row.get("Type") or "").strip().lower()

                # 'variable' rows are parent placeholders with no price — skip them
                if product_type == "variable":
                    continue

                # Resolve price: prefer Regular price, fall back to Sale price
                price = _safe_price(row.get("Regular price")) or _safe_price(row.get("Sale price"))
                if price is None:
                    continue

                row_id = (row.get("ID") or "").strip()
                sku = (row.get("SKU") or "").strip()
                name = _strip_html(row.get("Name") or "")
                short_desc = _strip_html(row.get("Short description") or "")
                long_desc = _strip_html(row.get("Description") or "")

                # Merge descriptions: prefer short_desc; append long_desc if present
                description = short_desc
                if long_desc and long_desc != short_desc:
                    description = f"{short_desc} {long_desc}".strip() if short_desc else long_desc

                # Categories: strip escaped commas WooCommerce adds
                raw_cats = (row.get("Categories") or "").replace("\\,", ",")
                # Keep only the leaf-level part after " > " for cleaner display
                cat_parts = [c.strip() for c in raw_cats.split(",") if c.strip()]
                categories = "; ".join(cat_parts)

                # Fallback: if description is empty, generate one from name + categories
                if not description and name:
                    leaf_cats = [c.split(" > ")[-1].strip() for c in raw_cats.split(",") if " > " in c]
                    cat_label = leaf_cats[0] if leaf_cats else (cat_parts[-1] if cat_parts else "")
                    description = f"{name} is a golf product" + (f" in the {cat_label} category" if cat_label else "") + f" priced at ${price}."

                # First image URL for reference
                images_raw = (row.get("Images") or "").strip()
                first_image = images_raw.split(",")[0].strip() if images_raw else ""

                entry_id = row_id or sku or name.lower().replace(" ", "-")

                products.append(ProductDetails(
                    entry_id=entry_id,
                    name=name or entry_id,
                    slug=sku or entry_id,
                    sku=sku or entry_id,
                    description=description,
                    categories=categories,
                    price=price,
                    properties={"image": first_image, "type": product_type},
                ))

        return products

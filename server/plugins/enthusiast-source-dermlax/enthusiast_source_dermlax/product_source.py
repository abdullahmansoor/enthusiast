# plugins/enthusiast_source_sample/source.py

import csv, json
from pathlib import Path
from typing import Any, Dict, List
from collections import defaultdict
from enthusiast_common import ProductDetails, ProductSourcePlugin

class DermlaxProductSource(ProductSourcePlugin):
    """
    Hard-coded CSV, no external config.
    Preserves ALL columns under properties.* so nothing is lost.
    Flip GROUP_VARIANTS to True to get one product per Handle with variants grouped.
    """

    # ---- Hard-coded knobs you can tweak in code ----
    CSV_FILENAME = "products_export_1.csv"   # file must live next to this source.py
    GROUP_VARIANTS = False                   # False => variant-as-product; True => group by Handle
    MERGE_TAGS_INTO_CATEGORIES = False       # optionally merge 'Tags' into categories

    # Core field mapping (promoted to top-level ProductDetails)
    CORE_MAP = {
        "entry_id": "Variant SKU",           # if GROUP_VARIANTS=True we’ll switch to Handle at runtime
        "name": "Title",
        "slug": "Handle",
        "sku": "Variant SKU",
        "description": "Body (HTML)",
        "categories": "Product Category",
        "price": "Variant Price",
    }

    # Helpful buckets to keep structure in properties
    VARIANT_FIELDS = [
        "Variant SKU","Variant Price","Variant Compare At Price","Variant Barcode",
        "Variant Weight Unit","Variant Tax Code","Variant Inventory Qty",
        "Variant Inventory Policy","Variant Inventory Tracker","Variant Requires Shipping",
        "Variant Taxable","Option1 Name","Option1 Value","Option2 Name","Option2 Value",
        "Option3 Name","Option3 Value","Variant Image",
    ]
    MEDIA_FIELDS = ["Image Src","Image Alt Text","Image Position"]
    SEO_FIELDS = [
        "SEO Title","SEO Description","Google Shopping / Google Product Category",
        "Google Shopping / Gender","Google Shopping / Age Group",
        "Google Shopping / MPN","Google Shopping / Condition",
        "Google Shopping / Custom Product","Google Shopping / Custom Label 0",
        "Google Shopping / Custom Label 1","Google Shopping / Custom Label 2",
        "Google Shopping / Custom Label 3","Google Shopping / Custom Label 4",
        "Google: Custom Product (product.metafields.mm-google-shopping.custom_product)",
    ]
    COMMERCE_FIELDS = ["Vendor","Type","Status","Cost per item","Gift Card","Published","Variant Fulfillment Service"]
    SKIN_ATTR_FIELDS = [
        "Skin care effect (product.metafields.shopify.skin-care-effect)",
        "Skin care features (product.metafields.shopify.skin-care-features)",
        "Skin tone (product.metafields.shopify.skin-tone)",
        "Suitable for skin type (product.metafields.shopify.suitable-for-skin-type)",
        "Product form (product.metafields.shopify.product-form)",
        "Cosmetic function (product.metafields.shopify.cosmetic-function)",
        "Cosmetic finish (product.metafields.shopify.cosmetic-finish)",
        "Makeup features (product.metafields.shopify.makeup-features)",
        "Makeup shade (product.metafields.shopify.makeup-color-shade)",
        "Constitutive ingredients (product.metafields.shopify.constitutive-ingredients)",
        "Detailed ingredients (product.metafields.shopify.detailed-ingredients)",
        "Package type (product.metafields.shopify.package-type)",
        "Dispenser type (product.metafields.shopify.dispenser-type)",
        "Flavor (product.metafields.shopify.flavor)",
        "Product certifications & standards (product.metafields.shopify.product-certifications-standards)",
        "Age group (product.metafields.shopify.age-group)",
    ]

    def __init__(self, data_set_id: Any):
        super().__init__(data_set_id)
        # Hard-coded CSV path next to this file
        self.sample_file_path = Path(__file__).with_name(self.CSV_FILENAME)

    # ---------- helpers to keep code tidy & preserve all columns ----------

    @staticmethod
    def _val(row: Dict[str, str], key: str) -> str:
        return (row.get(key) or "").strip()

    def _safe_price(self, row: Dict[str, str]) -> str:
        """Return a valid numeric string or None if price is missing/invalid."""
        raw = (row.get(self.CORE_MAP["price"]) or "").strip()
        try:
            if raw:
                # Remove common formatting symbols (e.g. $)
                return str(float(raw.replace("$", "").replace(",", "")))
        except Exception:
            pass
        return None

    def _categories_from(self, row: Dict[str, str]) -> str:
        cats: list[str] = []
        base = self._val(row, self.CORE_MAP.get("categories", "Product Category"))
        if base:
            cats.append(base)
        if getattr(self, "MERGE_TAGS_INTO_CATEGORIES", False):
            tags = self._val(row, "Tags")
            if tags:
                cats.extend(t.strip() for t in tags.split(",") if t.strip())
        return "; ".join(cats)

    def _build_media(self, rows: List[Dict[str,str]]) -> List[Dict[str,str]]:
        media = []
        for r in rows:
            src = self._val(r, "Image Src")
            if src:
                media.append({
                    "src": src,
                    "alt": self._val(r, "Image Alt Text"),
                    "position": self._val(r, "Image Position"),
                })
        # de-dupe by (src, alt)
        uniq = {(m["src"], m.get("alt","")): m for m in media if m.get("src")}
        def pos(m): 
            try: return int(m.get("position") or 0)
            except: return 0
        return sorted(uniq.values(), key=pos)

    def _build_seo(self, row: Dict[str,str]) -> Dict[str,str]:
        return {k: self._val(row,k) for k in self.SEO_FIELDS if self._val(row,k)}

    def _build_commerce(self, row: Dict[str,str]) -> Dict[str,str]:
        return {k: self._val(row,k) for k in self.COMMERCE_FIELDS if self._val(row,k)}

    def _build_skin_attrs(self, row: Dict[str,str]) -> Dict[str,str]:
        return {k: self._val(row,k) for k in self.SKIN_ATTR_FIELDS if self._val(row,k)}

    def _build_variant(self, row: Dict[str,str]) -> Dict[str,str]:
        return {k: self._val(row,k) for k in self.VARIANT_FIELDS if k in row}

    # ------------------------- main fetch logic ---------------------------

    def fetch(self) -> List[ProductDetails]:
        rows = list(csv.DictReader(self.sample_file_path.open(newline="", encoding="utf-8-sig")))
        if self.GROUP_VARIANTS:
            return self._fetch_grouped(rows)
        return self._fetch_variant_as_product(rows)

    # Variant-as-product: fastest, no info loss (all columns kept in properties)
    def _fetch_variant_as_product(self, rows: List[Dict[str,str]]) -> List[ProductDetails]:
        out: List[ProductDetails] = []
        for r in rows:
            entry_id = self._val(r, self.CORE_MAP["entry_id"]) or self._val(r, "Handle")
            name     = self._val(r, self.CORE_MAP["name"])
            slug     = self._val(r, self.CORE_MAP["slug"])
            sku      = self._val(r, self.CORE_MAP["sku"]) or entry_id
            desc     = self._val(r, self.CORE_MAP["description"])
            #price    = self._val(r, self.CORE_MAP["price"])

            price = self._safe_price(r)
            if price is None:
                # skip products with no valid price
                continue
            if float(price) == 0:
                # skip zero-price test/placeholder entries
                continue
            if self._val(r, "Status") == "draft":
                # skip unpublished draft products
                continue
            cats     = self._categories_from(r)

            props = {
                "media": self._build_media([r]),
                "seo": self._build_seo(r),
                "commerce": self._build_commerce(r),
                "skin_attributes": self._build_skin_attrs(r),
                "variant": self._build_variant(r),
                "raw_row": r,  # << keeps EVERY original column
            }

            out.append(ProductDetails(
                entry_id=entry_id, name=name or slug or entry_id, slug=slug,
                sku=sku, description=desc, properties=props, categories=cats, price=price
            ))
        return out

    # Group by Handle: one product with variants[] and price range; preserves all rows
    def _fetch_grouped(self, rows: List[Dict[str,str]]) -> List[ProductDetails]:
        buckets = defaultdict(list)
        for r in rows:
            h = self._val(r, "Handle")
            if h:
                buckets[h].append(r)

        out: List[ProductDetails] = []
        for handle, group in buckets.items():
            root = group[0]
            name = self._val(root, self.CORE_MAP["name"]) or handle
            desc = self._val(root, self.CORE_MAP["description"])
            cats = self._categories_from(root)

            variants = [self._build_variant(r) for r in group if self._val(r, "Variant SKU")]
            prices = []
            for v in variants:
                try:
                    if v.get("Variant Price"):
                        prices.append(float(v["Variant Price"]))
                except Exception:
                    pass
            price_min = min(prices) if prices else None
            price_max = max(prices) if prices else None

            props = {
                "media": self._build_media(group),
                "seo": self._build_seo(root),
                "commerce": self._build_commerce(root),
                "skin_attributes": self._build_skin_attrs(root),
                "variants": variants,
                "price_min": price_min,
                "price_max": price_max,
                "raw_rows": group,  # << preserves ALL original rows/columns
            }

            out.append(ProductDetails(
                entry_id=handle,
                name=name,
                slug=handle,
                sku=self._val(root, "Variant SKU") or handle,  # representative sku
                description=desc,
                properties=props,
                categories=cats,
                price=(str(price_min) if price_min is not None else self._val(root, self.CORE_MAP["price"])),
            ))
        return out

# ---------------------------------------------------------------------- #
# Main test entry point (stand-alone usage)
# ---------------------------------------------------------------------- #
def main():
    """
    Quick standalone test to verify CSV parsing.
    """
    print("🔍 Testing SampleProductSource with hard-coded CSV...")
    src = DermlaxProductSource(data_set_id="test")
    products = src.fetch()

    print(f"✅ Loaded {len(products)} products.")
    # print first few with partial properties
    for i, p in enumerate(products[:3]):
        print(f"\n[{i+1}] {p.name} (SKU: {p.sku})")
        print(f"   Categories: {p.categories}")
        print(f"   Price: {p.price}")
        print(f"   Description: {p.description[:120]}...")
        print(f"   Skin Attributes: {list(p.properties.get('skin_attributes', {}).keys())[:5]}")
        print(f"   Media Count: {len(p.properties.get('media', []))}")
        print(f"   Keys in properties: {list(p.properties.keys())}")
    print("\n✅ Test run complete.")


if __name__ == "__main__":
    main()
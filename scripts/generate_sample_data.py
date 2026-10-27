"""Write deterministic synthetic raw extracts for the Lumen & Field retailer.

Run from the repository root:

    python scripts/generate_sample_data.py

The seed is fixed, so the CSV files do not drift between machines.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

STORES = [
    ("S01", "Berlin Flagship", "Berlin", "Germany", "DACH", "Flagship"),
    ("S02", "Munich Outlet", "Munich", "Germany", "DACH", "Outlet"),
    ("S03", "Hamburg Flagship", "Hamburg", "Germany", "DACH", "Flagship"),
    ("S04", "Vienna Flagship", "Vienna", "Austria", "DACH", "Flagship"),
    ("S05", "Salzburg Outlet", "Salzburg", "Austria", "DACH", "Outlet"),
    ("S06", "Amsterdam Flagship", "Amsterdam", "Netherlands", "BENELUX", "Flagship"),
    ("S07", "Rotterdam Outlet", "Rotterdam", "Netherlands", "BENELUX", "Outlet"),
    ("S08", "Web EU", "Berlin", "Germany", "DACH", "Web"),
]

PROMOTIONS = [
    ("WELCOME10", "Welcome 10 Percent", "2024-01-01", "2025-06-30"),
    ("SPRING15", "Spring 15 Percent", "2024-03-01", "2024-05-31"),
    ("BULK20", "Bulk 20 Percent", "2024-01-01", "2025-06-30"),
]

PROMO_RATES = {
    "WELCOME10": "0.10",
    "SPRING15": "0.15",
    "BULK20": "0.20",
}

PRODUCTS = [
    ("SKU-1001", "Arc Pendant", "Lighting", "Pendants", "Nordlicht", 4200, "true"),
    ("SKU-1002", "Harbor Table Lamp", "Lighting", "Lamps", "Nordlicht", 2800, "true"),
    ("SKU-1003", "Field Sconce", "Lighting", "Lamps", "Osterlin", 1900, "true"),
    ("SKU-1004", "Linen Shade Bulb Set", "Lighting", "Bulbs", "Kleinware", 800, "true"),
    ("SKU-1101", "Oak Throw", "Textiles", "Throws", "Sable", 3500, "true"),
    ("SKU-1102", "Harbor Cushion", "Textiles", "Cushions", "Sable", 1800, "true"),
    ("SKU-1103", "Field Curtain Pair", "Textiles", "Curtains", "Atelier Feld", 6400, "true"),
    ("SKU-1104", "Linen Napkin Set", "Textiles", "Throws", "Atelier Feld", 1200, "false"),
    ("SKU-1201", "Stoneware Bowl", "Tabletop", "Ceramics", "Hafen & Co", 1600, "true"),
    ("SKU-1202", "Ripple Glass Carafe", "Tabletop", "Glass", "Hafen & Co", 2400, "true"),
    ("SKU-1203", "Matte Cutlery Set", "Tabletop", "Cutlery", "Kleinware", 3900, "true"),
    ("SKU-1204", "Espresso Cup Pair", "Tabletop", "Ceramics", "Osterlin", 1400, "true"),
    ("SKU-1301", "Seagrass Basket", "Storage", "Baskets", "Kleinware", 2200, "true"),
    ("SKU-1302", "Oak Wall Shelf", "Storage", "Shelves", "Nordlicht", 5200, "true"),
    ("SKU-1303", "Lidded Box", "Storage", "Boxes", "Sable", 1500, "true"),
    ("SKU-1304", "Wire Basket", "Storage", "Baskets", "Osterlin", 1100, "false"),
    ("SKU-1401", "Terracotta Planter", "Outdoor", "Planters", "Atelier Feld", 2700, "true"),
    ("SKU-1402", "Brass Lantern", "Outdoor", "Lanterns", "Nordlicht", 4600, "true"),
    ("SKU-1403", "Outdoor Seat Pad", "Outdoor", "Textiles", "Sable", 2100, "true"),
    ("SKU-1404", "Herb Pot Trio", "Outdoor", "Planters", "Hafen & Co", 1800, "true"),
    ("SKU-1501", "Marble Tray", "Tabletop", "Ceramics", "Atelier Feld", 3100, "true"),
    ("SKU-1502", "Smoke Tumbler Set", "Tabletop", "Glass", "Hafen & Co", 2000, "true"),
    ("SKU-1503", "Wool Cushion", "Textiles", "Cushions", "Sable", 2600, "true"),
    ("SKU-1504", "Floor Lantern", "Lighting", "Lamps", "Osterlin", 7300, "true"),
]

FIRST_NAMES = [
    "Mia",
    "Jonas",
    "Elena",
    "Lars",
    "Sofie",
    "Noah",
    "Emma",
    "Felix",
    "Nora",
    "Owen",
    "Lina",
    "Hugo",
    "Mila",
    "Anton",
    "Iris",
    "Theo",
]
LAST_NAMES = [
    "Schmidt",
    "Keller",
    "Vogel",
    "Bach",
    "Hoffmann",
    "Meier",
    "Wolf",
    "Kruger",
    "Schneider",
    "Fischer",
    "Weber",
    "Wagner",
    "Becker",
    "Richter",
    "Klein",
]
CITIES = {
    "Germany": ["Berlin", "Munich", "Hamburg", "Cologne", "Leipzig"],
    "Austria": ["Vienna", "Salzburg", "Graz"],
    "Netherlands": ["Amsterdam", "Rotterdam", "Utrecht"],
}
SEGMENTS = ["Consumer", "Consumer", "Consumer", "Professional", "Trade"]


def main() -> None:
    rng = random.Random(SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    customers = _customers(rng)
    orders, lines = _orders(rng, customers)
    _write(
        "customers.csv",
        ["customer_id", "full_name", "email", "segment", "city", "country", "signup_date"],
        customers,
    )
    _write(
        "products.csv",
        ["sku", "product_name", "category", "subcategory", "brand", "unit_cost", "is_active"],
        [_product_row(product) for product in PRODUCTS],
    )
    _write(
        "stores.csv",
        ["store_id", "store_name", "city", "country", "region", "store_format"],
        [list(store) for store in STORES],
    )
    _write(
        "promotions.csv",
        ["promo_code", "promo_name", "start_date", "end_date"],
        [list(promo) for promo in PROMOTIONS],
    )
    _write(
        "orders.csv",
        ["order_id", "order_datetime", "customer_id", "store_id", "channel", "status", "promo_code"],
        orders,
    )
    _write(
        "order_lines.csv",
        ["order_line_id", "order_id", "sku", "quantity", "unit_price", "discount_pct"],
        lines,
    )
    print(f"wrote {len(orders)} orders and {len(lines)} lines to {OUTPUT_DIR}")


def _customers(rng: random.Random) -> list[list[str]]:
    rows = [
        ["C001", "  mia schmidt  ", "Mia.Schmidt@Example.COM", "consumer", "Berlin", " de ", "2022-04-18"],
        ["C002", "Lars Vogel", "lars.vogel@example.com", "Professional", "Amsterdam", "Holland", "2021-11-02"],
    ]
    for number in range(3, 101):
        country = rng.choices(["Germany", "Austria", "Netherlands"], weights=[6, 2, 2], k=1)[0]
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        email = "" if number % 17 == 0 else f"{first}.{last}@example.com".lower()
        signup = date(2021, 1, 1) + timedelta(days=rng.randrange(900))
        rows.append(
            [
                f"C{number:03d}",
                f"{first} {last}",
                email,
                rng.choice(SEGMENTS),
                rng.choice(CITIES[country]),
                country,
                signup.isoformat(),
            ]
        )
    rows.append(["C001", "Duplicate Mia", "dup@example.com", "Consumer", "Berlin", "Germany", "2023-01-01"])
    return rows


def _orders(rng: random.Random, customers: list[list[str]]) -> tuple[list[list[str]], list[list[str]]]:
    customer_ids = [row[0] for row in customers if row[0] != "C001" or row[2] != "dup@example.com"]
    # The duplicate C001 row is last; customer_ids still contains the first C001 once
    # because both rows share the id. Deduplicate while preserving order.
    seen: set[str] = set()
    unique_customers: list[str] = []
    for customer_id in customer_ids:
        if customer_id not in seen:
            seen.add(customer_id)
            unique_customers.append(customer_id)

    list_prices = {sku: _list_price(cost) for sku, _, _, _, _, cost, _ in PRODUCTS}
    start = date(2024, 1, 1)
    span_days = (date(2025, 6, 30) - start).days
    orders: list[list[str]] = []
    lines: list[list[str]] = []
    line_number = 1
    for index in range(400):
        order_id = f"ORD-{1000 + index}"
        order_day = start + timedelta(days=rng.randrange(span_days + 1))
        stamp = order_day.isoformat() + f"T{rng.randrange(9, 19):02d}:{rng.randrange(0, 60):02d}:00"
        store_id = rng.choice(STORES)[0]
        if store_id == "S08" or rng.random() < 0.28:
            channel = "Web"
        else:
            channel = "Store"
        roll = rng.random()
        if roll < 0.05:
            status = "cancelled"
        elif roll < 0.12:
            status = "returned"
        else:
            status = "completed"
        if rng.random() < 0.32:
            promo_code = rng.choice(list(PROMO_RATES))
            discount = PROMO_RATES[promo_code]
        else:
            promo_code = ""
            discount = "0"
        customer_id = rng.choice(unique_customers)
        orders.append([order_id, stamp, customer_id, store_id, channel, status, promo_code])
        for _ in range(rng.randint(1, 3)):
            sku = rng.choice(PRODUCTS)[0]
            lines.append(
                [
                    f"LN-{line_number:05d}",
                    order_id,
                    sku,
                    str(rng.randint(1, 3)),
                    list_prices[sku],
                    discount,
                ]
            )
            line_number += 1

    for order in orders:
        if order[0] == "ORD-1000":
            order[1] = "2024-06-15T11:00:00"
            order[2] = "C003"
            order[3] = "S01"
            order[4] = "Store"
            order[5] = "completed"
            order[6] = ""

    orders.extend(
        [
            ["BAD-CANCEL", "2024-07-01T10:00:00", "C003", "S01", "Store", "cancelled", ""],
            ["BAD-CUSTOMER", "2024-07-02T10:00:00", "NOBODY", "S01", "Store", "completed", ""],
            ["BAD-STORE", "2024-07-03T10:00:00", "C003", "NOSTORE", "Store", "completed", ""],
            ["BAD-PROMO", "2024-07-04T10:00:00", "C003", "S01", "Web", "completed", "NOTREAL"],
            ["BAD-CHANNEL", "2024-07-05T10:00:00", "C003", "S01", "carrier-pigeon", "completed", ""],
        ]
    )
    lines.extend(
        [
            ["BL-CANCEL", "BAD-CANCEL", "SKU-1001", "1", "76.36", "0"],
            ["BL-CUSTOMER", "BAD-CUSTOMER", "SKU-1001", "1", "76.36", "0"],
            ["BL-STORE", "BAD-STORE", "SKU-1001", "1", "76.36", "0"],
            ["BL-PROMO", "BAD-PROMO", "SKU-1001", "1", "76.36", "0"],
            ["BL-CHANNEL", "BAD-CHANNEL", "SKU-1001", "1", "76.36", "0"],
            ["BL-ORPHAN", "ORD-MISSING", "SKU-1001", "1", "76.36", "0"],
            ["BL-SKU", "ORD-1000", "MISSING-SKU", "1", "10.00", "0"],
            ["BL-QTY", "ORD-1000", "SKU-1001", "0", "10.00", "0"],
            ["BL-DISC", "ORD-1000", "SKU-1001", "1", "10.00", "1.5"],
            ["BL-PRICE", "ORD-1000", "SKU-1001", "1", "-5.00", "0"],
            ["BL-DUP", "ORD-1000", "SKU-1002", "1", "50.91", "0"],
            ["BL-DUP", "ORD-1000", "SKU-1002", "2", "50.91", "0"],
        ]
    )
    return orders, lines


def _product_row(product: tuple[str, str, str, str, str, int, str]) -> list[str]:
    sku, name, category, subcategory, brand, cost_cents, active = product
    return [sku, name, category, subcategory, brand, _money(cost_cents), active]


def _list_price(cost_cents: int) -> str:
    return _money(round(cost_cents / 0.55))


def _money(cents: int) -> str:
    return f"{cents / 100:.2f}"


def _write(filename: str, header: list[str], rows: list[list[str]]) -> None:
    path = OUTPUT_DIR / filename
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


if __name__ == "__main__":
    main()

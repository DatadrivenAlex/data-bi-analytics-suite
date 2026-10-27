"""Clean raw retail extracts and conform them to a sales star schema.

Grain of ``fact_sales`` is one accepted order line. Cancelled orders never
reach the fact. A returned order stays in the fact with ``net_amount`` of 0
and the original ticket recorded in ``return_amount`` (goods assumed resalable;
damage and partial returns are out of scope).
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import pandas as pd

from bi_analytics.dates import as_date, day_index, iso_or_none
from bi_analytics.money import ZERO, money, to_decimal
from bi_analytics.schema import (
    DIM_CUSTOMER_COLUMNS,
    DIM_DATE_COLUMNS,
    DIM_PRODUCT_COLUMNS,
    DIM_PROMOTION_COLUMNS,
    DIM_STORE_COLUMNS,
    FACT_SALES_COLUMNS,
    REJECT_COLUMNS,
)

COUNTRY_ALIASES = {
    "de": "Germany",
    "germany": "Germany",
    "deutschland": "Germany",
    "at": "Austria",
    "austria": "Austria",
    "österreich": "Austria",
    "osterreich": "Austria",
    "nl": "Netherlands",
    "netherlands": "Netherlands",
    "holland": "Netherlands",
    "the netherlands": "Netherlands",
}

SEGMENTS = {"Consumer", "Professional", "Trade", "Unknown"}
STORE_FORMATS = {"Flagship", "Outlet", "Web"}
CHANNELS = {"web": "Web", "online": "Web", "store": "Store", "retail": "Store"}
STATUSES = {
    "completed": "completed",
    "complete": "completed",
    "returned": "returned",
    "return": "returned",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}
NO_PROMOTION = "NONE"
RATE_PLACES = Decimal("0.0001")


@dataclass
class StarSchema:
    """Conformed dimensions, the sales fact, and the quarantine list."""

    dim_date: pd.DataFrame
    dim_customer: pd.DataFrame
    dim_product: pd.DataFrame
    dim_store: pd.DataFrame
    dim_promotion: pd.DataFrame
    fact_sales: pd.DataFrame
    rejects: pd.DataFrame

    def tables(self) -> dict[str, pd.DataFrame]:
        return {
            "dim_date": self.dim_date,
            "dim_customer": self.dim_customer,
            "dim_product": self.dim_product,
            "dim_store": self.dim_store,
            "dim_promotion": self.dim_promotion,
            "fact_sales": self.fact_sales,
        }


def build_star_schema(raw: dict[str, pd.DataFrame]) -> StarSchema:
    """Transform raw frames into a referentially intact star schema."""
    rejects: list[dict[str, str]] = []
    customers = _conform_customers(raw["customers"], rejects)
    products = _conform_products(raw["products"], rejects)
    stores = _conform_stores(raw["stores"], rejects)
    promotions = _conform_promotions(raw["promotions"], rejects)
    orders = _index_orders(raw["orders"], rejects)
    lines = _prepare_lines(raw["order_lines"], rejects)

    customer_ids = set(customers["customer_id"])
    store_ids = set(stores["store_id"])
    promo_codes = set(promotions["promo_code"])
    skus = set(products["sku"])
    product_cost = {
        row.sku: to_decimal(row.unit_cost) or ZERO for row in products.itertuples(index=False)
    }

    accepted_orders: dict[str, dict[str, object]] = {}
    rejected_orders: dict[str, str] = {}
    for order_id, order in orders.items():
        reason = _order_rejection_reason(order, customer_ids, store_ids, promo_codes)
        if reason is not None:
            rejected_orders[order_id] = reason
            continue
        accepted_orders[order_id] = order

    seen_lines: set[str] = set()
    fact_rows: list[dict[str, object]] = []
    for line in lines:
        order_id = line["order_id"]
        line_id = line["order_line_id"]
        if order_id in rejected_orders:
            _add_reject(
                rejects,
                rejected_orders[order_id],
                "order_line",
                order_id,
                line_id,
                "Order failed a header rule",
            )
            continue
        if order_id not in accepted_orders:
            _add_reject(
                rejects,
                "missing_order",
                "order_line",
                order_id,
                line_id,
                "order_id not in orders",
            )
            continue
        if line_id in seen_lines:
            _add_reject(
                rejects,
                "duplicate_line",
                "order_line",
                order_id,
                line_id,
                "Repeated order_line_id; first occurrence kept",
            )
            continue
        seen_lines.add(line_id)
        reason = _line_rejection_reason(line, skus)
        if reason is not None:
            _add_reject(rejects, reason, "order_line", order_id, line_id, line["detail"])
            continue
        order = accepted_orders[order_id]
        sku = str(line["sku"])
        fact_rows.append(_fact_row(order, line, product_cost[sku]))

    fact_rows.sort(key=lambda row: (str(row["order_date"]), str(row["order_id"]), str(row["order_line_id"])))
    fact = pd.DataFrame(fact_rows)
    dim_date = _build_dim_date(fact)
    dim_customer = _with_key(customers, "customer_key", "customer_id", DIM_CUSTOMER_COLUMNS)
    dim_product = _with_key(products, "product_key", "sku", DIM_PRODUCT_COLUMNS)
    dim_store = _with_key(stores, "store_key", "store_id", DIM_STORE_COLUMNS)
    dim_promotion = _with_key(promotions, "promotion_key", "promo_code", DIM_PROMOTION_COLUMNS)
    # NONE must stay key 1 so "no promotion" is stable even if other codes sort first.
    dim_promotion = _pin_no_promotion(dim_promotion)
    fact = _apply_dimension_keys(fact, dim_date, dim_customer, dim_product, dim_store, dim_promotion)

    return StarSchema(
        dim_date=_frame(dim_date, DIM_DATE_COLUMNS),
        dim_customer=_frame(dim_customer, DIM_CUSTOMER_COLUMNS),
        dim_product=_frame(dim_product, DIM_PRODUCT_COLUMNS),
        dim_store=_frame(dim_store, DIM_STORE_COLUMNS),
        dim_promotion=_frame(dim_promotion, DIM_PROMOTION_COLUMNS),
        fact_sales=_frame(fact, FACT_SALES_COLUMNS),
        rejects=_frame(pd.DataFrame(rejects), REJECT_COLUMNS),
    )


def _conform_customers(frame: pd.DataFrame, rejects: list[dict[str, str]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for record in _records(frame):
        customer_id = _text(record.get("customer_id"))
        if customer_id == "":
            _add_reject(rejects, "missing_customer_id", "customer", "", "", "customer_id is blank")
            continue
        if customer_id in seen:
            _add_reject(
                rejects,
                "duplicate_customer",
                "customer",
                "",
                "",
                customer_id,
            )
            continue
        country = COUNTRY_ALIASES.get(_text(record.get("country")).casefold())
        if country is None:
            _add_reject(
                rejects,
                "unknown_country",
                "customer",
                "",
                "",
                _text(record.get("country")) or customer_id,
            )
            continue
        seen.add(customer_id)
        segment = _text(record.get("segment")).title()
        if segment not in SEGMENTS:
            segment = "Unknown"
        email = _text(record.get("email")).lower()
        rows.append(
            {
                "customer_id": customer_id,
                "full_name": _title_name(record.get("full_name")),
                "email": email,
                "segment": segment,
                "city": _text(record.get("city")).title(),
                "country": country,
                "signup_date": iso_or_none(record.get("signup_date")),
            }
        )
    return _frame(pd.DataFrame(rows), [column for column in DIM_CUSTOMER_COLUMNS if column != "customer_key"])


def _conform_products(frame: pd.DataFrame, rejects: list[dict[str, str]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for record in _records(frame):
        sku = _text(record.get("sku")).upper()
        if sku == "":
            _add_reject(rejects, "missing_sku", "product", "", "", "sku is blank")
            continue
        if sku in seen:
            _add_reject(rejects, "duplicate_sku", "product", "", "", sku)
            continue
        unit_cost = to_decimal(record.get("unit_cost"))
        if unit_cost is None or unit_cost < 0:
            _add_reject(rejects, "invalid_unit_cost", "product", "", "", sku)
            continue
        seen.add(sku)
        rows.append(
            {
                "sku": sku,
                "product_name": _text(record.get("product_name")),
                "category": _text(record.get("category")).title(),
                "subcategory": _text(record.get("subcategory")).title(),
                "brand": _text(record.get("brand")),
                "unit_cost": f"{money(unit_cost):.2f}",
                "is_active": _parse_bool(record.get("is_active")),
            }
        )
    return _frame(pd.DataFrame(rows), [column for column in DIM_PRODUCT_COLUMNS if column != "product_key"])


def _conform_stores(frame: pd.DataFrame, rejects: list[dict[str, str]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for record in _records(frame):
        store_id = _text(record.get("store_id")).upper()
        if store_id == "":
            _add_reject(rejects, "missing_store_id", "store", "", "", "store_id is blank")
            continue
        if store_id in seen:
            _add_reject(rejects, "duplicate_store", "store", "", "", store_id)
            continue
        country = COUNTRY_ALIASES.get(_text(record.get("country")).casefold())
        if country is None:
            _add_reject(rejects, "unknown_country", "store", "", "", store_id)
            continue
        seen.add(store_id)
        store_format = _text(record.get("store_format")).title()
        if store_format not in STORE_FORMATS:
            store_format = "Unknown"
        rows.append(
            {
                "store_id": store_id,
                "store_name": _text(record.get("store_name")),
                "city": _text(record.get("city")).title(),
                "country": country,
                "region": _text(record.get("region")).upper(),
                "store_format": store_format,
            }
        )
    return _frame(pd.DataFrame(rows), [column for column in DIM_STORE_COLUMNS if column != "store_key"])


def _conform_promotions(frame: pd.DataFrame, rejects: list[dict[str, str]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = [
        {
            "promo_code": NO_PROMOTION,
            "promo_name": "No Promotion",
            "start_date": None,
            "end_date": None,
        }
    ]
    seen = {NO_PROMOTION}
    for record in _records(frame):
        promo_code = _text(record.get("promo_code")).upper()
        if promo_code == "":
            _add_reject(rejects, "missing_promo_code", "promotion", "", "", "promo_code is blank")
            continue
        if promo_code in seen:
            _add_reject(rejects, "duplicate_promotion", "promotion", "", "", promo_code)
            continue
        seen.add(promo_code)
        rows.append(
            {
                "promo_code": promo_code,
                "promo_name": _text(record.get("promo_name")),
                "start_date": iso_or_none(record.get("start_date")),
                "end_date": iso_or_none(record.get("end_date")),
            }
        )
    return _frame(pd.DataFrame(rows), [column for column in DIM_PROMOTION_COLUMNS if column != "promotion_key"])


def _index_orders(frame: pd.DataFrame, rejects: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    orders: dict[str, dict[str, object]] = {}
    for record in _records(frame):
        order_id = _text(record.get("order_id"))
        if order_id == "":
            _add_reject(rejects, "missing_order_id", "order", "", "", "order_id is blank")
            continue
        if order_id in orders:
            _add_reject(rejects, "duplicate_order", "order", order_id, "", "Repeated order_id; first kept")
            continue
        order_date = as_date(record.get("order_datetime"))
        channel = CHANNELS.get(_text(record.get("channel")).casefold())
        status = STATUSES.get(_text(record.get("status")).casefold())
        promo_code = _text(record.get("promo_code")).upper() or NO_PROMOTION
        orders[order_id] = {
            "order_id": order_id,
            "order_date": order_date,
            "customer_id": _text(record.get("customer_id")),
            "store_id": _text(record.get("store_id")).upper(),
            "channel": channel,
            "status": status,
            "promo_code": promo_code,
        }
    return orders


def _prepare_lines(frame: pd.DataFrame, rejects: list[dict[str, str]]) -> list[dict[str, object]]:
    lines: list[dict[str, object]] = []
    for record in _records(frame):
        line_id = _text(record.get("order_line_id"))
        order_id = _text(record.get("order_id"))
        if line_id == "":
            _add_reject(rejects, "missing_line_id", "order_line", order_id, "", "order_line_id is blank")
            continue
        quantity = _parse_int(record.get("quantity"))
        unit_price = to_decimal(record.get("unit_price"))
        discount_pct = to_decimal(record.get("discount_pct"))
        detail = ""
        if quantity is None or quantity < 1:
            detail = f"quantity={_text(record.get('quantity'))}"
        elif unit_price is None or unit_price < 0:
            detail = f"unit_price={_text(record.get('unit_price'))}"
        elif discount_pct is None or discount_pct < 0 or discount_pct > 1:
            detail = f"discount_pct={_text(record.get('discount_pct'))}"
        lines.append(
            {
                "order_line_id": line_id,
                "order_id": order_id,
                "sku": _text(record.get("sku")).upper(),
                "quantity": quantity,
                "unit_price": unit_price,
                "discount_pct": discount_pct,
                "detail": detail,
            }
        )
    return lines


def _order_rejection_reason(
    order: dict[str, object],
    customer_ids: set[str],
    store_ids: set[str],
    promo_codes: set[str],
) -> str | None:
    if order["order_date"] is None:
        return "invalid_order_datetime"
    if order["status"] is None:
        return "invalid_status"
    if order["status"] == "cancelled":
        return "cancelled_order"
    if order["channel"] is None:
        return "invalid_channel"
    if order["customer_id"] not in customer_ids:
        return "unknown_customer"
    if order["store_id"] not in store_ids:
        return "unknown_store"
    if order["promo_code"] not in promo_codes:
        return "unknown_promotion"
    return None


def _line_rejection_reason(line: dict[str, object], skus: set[str]) -> str | None:
    if line["sku"] not in skus:
        return "unknown_sku"
    quantity = line["quantity"]
    if not isinstance(quantity, int) or quantity < 1:
        return "invalid_quantity"
    unit_price = line["unit_price"]
    if not isinstance(unit_price, Decimal) or unit_price < 0:
        return "invalid_price"
    discount_pct = line["discount_pct"]
    if not isinstance(discount_pct, Decimal) or discount_pct < 0 or discount_pct > 1:
        return "invalid_discount"
    return None


def _fact_row(
    order: dict[str, object],
    line: dict[str, object],
    unit_cost: Decimal,
) -> dict[str, object]:
    quantity = int(line["quantity"])  # type: ignore[arg-type]
    unit_price = money(line["unit_price"])  # type: ignore[arg-type]
    raw_discount = line["discount_pct"]
    assert isinstance(raw_discount, Decimal)
    discount_pct = raw_discount.quantize(RATE_PLACES)
    gross_amount = money(Decimal(quantity) * unit_price)
    discount_amount = money(gross_amount * discount_pct)
    extended_net = gross_amount - discount_amount
    returned = order["status"] == "returned"
    if returned:
        net_amount = ZERO
        cost_amount = ZERO
        return_amount = extended_net
    else:
        net_amount = extended_net
        cost_amount = money(Decimal(quantity) * unit_cost)
        return_amount = ZERO
    margin_amount = net_amount - cost_amount
    order_date = order["order_date"]
    assert isinstance(order_date, date)
    return {
        "order_line_id": line["order_line_id"],
        "order_id": order["order_id"],
        "order_date": order_date,
        "customer_id": order["customer_id"],
        "sku": line["sku"],
        "store_id": order["store_id"],
        "promo_code": order["promo_code"],
        "channel": order["channel"],
        "quantity": quantity,
        "unit_price": f"{unit_price:.2f}",
        "discount_pct": f"{discount_pct:.4f}",
        "gross_amount": f"{gross_amount:.2f}",
        "discount_amount": f"{discount_amount:.2f}",
        "net_amount": f"{net_amount:.2f}",
        "cost_amount": f"{cost_amount:.2f}",
        "margin_amount": f"{margin_amount:.2f}",
        "return_amount": f"{return_amount:.2f}",
        "is_returned": returned,
    }


def _build_dim_date(fact: pd.DataFrame) -> pd.DataFrame:
    if fact.empty or "order_date" not in fact.columns:
        return _frame(pd.DataFrame(), DIM_DATE_COLUMNS)
    dates = sorted({parsed for parsed in (as_date(row) for row in fact["order_date"]) if parsed is not None})
    if not dates:
        return _frame(pd.DataFrame(), DIM_DATE_COLUMNS)
    start, end = dates[0], dates[-1]
    rows: list[dict[str, object]] = []
    cursor = start
    while cursor <= end:
        rows.append(
            {
                "date_key": int(cursor.strftime("%Y%m%d")),
                "full_date": cursor.isoformat(),
                "year": cursor.year,
                "quarter": (cursor.month - 1) // 3 + 1,
                "month": cursor.month,
                "month_name": calendar.month_name[cursor.month],
                "day_of_month": cursor.day,
                "day_name": calendar.day_name[cursor.weekday()],
                "iso_week": cursor.isocalendar().week,
                "is_weekend": cursor.weekday() >= 5,
                "day_index": day_index(cursor),
            }
        )
        cursor += timedelta(days=1)
    return _frame(pd.DataFrame(rows), DIM_DATE_COLUMNS)


def _apply_dimension_keys(
    fact: pd.DataFrame,
    dim_date: pd.DataFrame,
    dim_customer: pd.DataFrame,
    dim_product: pd.DataFrame,
    dim_store: pd.DataFrame,
    dim_promotion: pd.DataFrame,
) -> pd.DataFrame:
    if fact.empty:
        return _frame(pd.DataFrame(), FACT_SALES_COLUMNS)
    date_key = {
        iso_or_none(row.full_date): int(row.date_key) for row in dim_date.itertuples(index=False)
    }
    customer_key = {
        row.customer_id: int(row.customer_key) for row in dim_customer.itertuples(index=False)
    }
    product_key = {row.sku: int(row.product_key) for row in dim_product.itertuples(index=False)}
    store_key = {row.store_id: int(row.store_key) for row in dim_store.itertuples(index=False)}
    promotion_key = {
        row.promo_code: int(row.promotion_key) for row in dim_promotion.itertuples(index=False)
    }
    rows: list[dict[str, object]] = []
    for index, record in enumerate(fact.to_dict(orient="records"), start=1):
        order_date = record["order_date"]
        rows.append(
            {
                "sales_key": index,
                "order_line_id": record["order_line_id"],
                "order_id": record["order_id"],
                "date_key": date_key[iso_or_none(order_date)],
                "customer_key": customer_key[record["customer_id"]],
                "product_key": product_key[record["sku"]],
                "store_key": store_key[record["store_id"]],
                "promotion_key": promotion_key[record["promo_code"]],
                "channel": record["channel"],
                "quantity": int(record["quantity"]),
                "unit_price": record["unit_price"],
                "discount_pct": record["discount_pct"],
                "gross_amount": record["gross_amount"],
                "discount_amount": record["discount_amount"],
                "net_amount": record["net_amount"],
                "cost_amount": record["cost_amount"],
                "margin_amount": record["margin_amount"],
                "return_amount": record["return_amount"],
                "is_returned": bool(record["is_returned"]),
            }
        )
    return _frame(pd.DataFrame(rows), FACT_SALES_COLUMNS)


def _with_key(frame: pd.DataFrame, key_name: str, natural_key: str, columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return _frame(pd.DataFrame(), columns)
    ordered = frame.sort_values(natural_key).reset_index(drop=True)
    ordered.insert(0, key_name, range(1, len(ordered) + 1))
    return _frame(ordered, columns)


def _pin_no_promotion(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    none_mask = frame["promo_code"] == NO_PROMOTION
    others = frame.loc[~none_mask].sort_values("promo_code")
    pinned = frame.loc[none_mask]
    ordered = pd.concat([pinned, others], ignore_index=True)
    ordered["promotion_key"] = range(1, len(ordered) + 1)
    return _frame(ordered, DIM_PROMOTION_COLUMNS)


def _frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=columns)
    for column in columns:
        if column not in frame.columns:
            frame[column] = None
    return frame.loc[:, columns].reset_index(drop=True)


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    if frame.empty:
        return []
    return frame.to_dict(orient="records")


def _add_reject(
    rejects: list[dict[str, str]],
    reason: str,
    entity: str,
    order_id: object,
    order_line_id: object,
    detail: object,
) -> None:
    rejects.append(
        {
            "reason": reason,
            "entity": entity,
            "order_id": "" if order_id is None else str(order_id),
            "order_line_id": "" if order_line_id is None else str(order_line_id),
            "detail": "" if detail is None else str(detail),
        }
    )


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _title_name(value: object) -> str:
    return " ".join(part.capitalize() for part in _text(value).split())


def _parse_int(value: object) -> int | None:
    text = _text(value)
    if text == "":
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    if number != number.to_integral_value():
        return None
    return int(number)


def _parse_bool(value: object) -> bool:
    text = _text(value).casefold()
    return text in {"1", "true", "yes", "y", "t"}


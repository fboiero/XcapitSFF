"""Quotes & Proposals — create, send, track, and export quotes.

Provides in-memory quote management with line-item calculations,
status lifecycle, duplication, and markdown export.
"""

import copy
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


# --- Enums ---


class QuoteStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


# --- Dataclasses ---


@dataclass
class LineItem:
    id: str
    description: str
    quantity: float
    unit_price: float
    discount_percent: float = 0.0
    tax_percent: float = 0.0

    @property
    def total(self) -> float:
        subtotal = self.quantity * self.unit_price
        discount = subtotal * self.discount_percent / 100
        after_discount = subtotal - discount
        tax = after_discount * self.tax_percent / 100
        return round(after_discount + tax, 2)


@dataclass
class Quote:
    id: str
    tenant_id: str
    deal_id: str
    quote_number: str
    title: str
    client_name: str
    client_email: str
    line_items: list[LineItem] = field(default_factory=list)
    subtotal: float = 0.0
    discount_total: float = 0.0
    tax_total: float = 0.0
    total: float = 0.0
    currency: str = "USD"
    status: QuoteStatus = QuoteStatus.DRAFT
    valid_until: str = ""
    notes: str = ""
    terms: str = ""
    created_by: str = ""
    created_at: str = ""
    sent_at: str | None = None
    viewed_at: str | None = None
    accepted_at: str | None = None


# --- Manager ---


class QuoteManager:
    """In-memory quote/proposal manager."""

    def __init__(self) -> None:
        self._quotes: dict[str, Quote] = {}
        self._counter: int = 0

    def _next_number(self) -> str:
        self._counter += 1
        return f"QT-{self._counter:04d}"

    @staticmethod
    def _calculate_totals(line_items: list[LineItem]) -> tuple[float, float, float, float]:
        """Return (subtotal, discount_total, tax_total, total)."""
        subtotal = 0.0
        discount_total = 0.0
        tax_total = 0.0
        for item in line_items:
            item_subtotal = item.quantity * item.unit_price
            item_discount = item_subtotal * item.discount_percent / 100
            item_after_discount = item_subtotal - item_discount
            item_tax = item_after_discount * item.tax_percent / 100
            subtotal += item_subtotal
            discount_total += item_discount
            tax_total += item_tax
        total = subtotal - discount_total + tax_total
        return (
            round(subtotal, 2),
            round(discount_total, 2),
            round(tax_total, 2),
            round(total, 2),
        )

    def _recalculate(self, quote: Quote) -> None:
        """Recalculate quote totals from line items."""
        quote.subtotal, quote.discount_total, quote.tax_total, quote.total = (
            self._calculate_totals(quote.line_items)
        )

    def create(
        self,
        tenant_id: str,
        deal_id: str,
        title: str,
        client_name: str,
        client_email: str,
        line_items: list[dict],
        *,
        valid_days: int = 30,
        notes: str = "",
        terms: str = "",
        created_by: str = "",
        currency: str = "USD",
    ) -> Quote:
        now = datetime.now(tz=None)
        items = [
            LineItem(
                id=str(uuid.uuid4()),
                description=li["description"],
                quantity=li.get("quantity", 1),
                unit_price=li["unit_price"],
                discount_percent=li.get("discount_percent", 0),
                tax_percent=li.get("tax_percent", 0),
            )
            for li in line_items
        ]
        subtotal, discount_total, tax_total, total = self._calculate_totals(items)

        quote = Quote(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            deal_id=deal_id,
            quote_number=self._next_number(),
            title=title,
            client_name=client_name,
            client_email=client_email,
            line_items=items,
            subtotal=subtotal,
            discount_total=discount_total,
            tax_total=tax_total,
            total=total,
            currency=currency,
            status=QuoteStatus.DRAFT,
            valid_until=(now + timedelta(days=valid_days)).isoformat(),
            notes=notes,
            terms=terms,
            created_by=created_by,
            created_at=now.isoformat(),
        )
        self._quotes[quote.id] = quote
        logger.info("Quote created: id=%s number=%s total=%.2f", quote.id, quote.quote_number, total)
        return quote

    def update(self, quote_id: str, **kwargs) -> Quote:
        quote = self._quotes.get(quote_id)
        if not quote:
            raise KeyError(f"Quote not found: {quote_id}")
        for key, value in kwargs.items():
            if hasattr(quote, key) and key not in ("id", "quote_number"):
                setattr(quote, key, value)
        logger.info("Quote updated: id=%s fields=%s", quote_id, list(kwargs.keys()))
        return quote

    def delete(self, quote_id: str) -> bool:
        if quote_id not in self._quotes:
            return False
        del self._quotes[quote_id]
        logger.info("Quote deleted: id=%s", quote_id)
        return True

    def get(self, quote_id: str) -> Quote:
        quote = self._quotes.get(quote_id)
        if not quote:
            raise KeyError(f"Quote not found: {quote_id}")
        return quote

    def list_quotes(
        self,
        tenant_id: str,
        deal_id: str | None = None,
        status: QuoteStatus | None = None,
    ) -> list[Quote]:
        results = [q for q in self._quotes.values() if q.tenant_id == tenant_id]
        if deal_id is not None:
            results = [q for q in results if q.deal_id == deal_id]
        if status is not None:
            results = [q for q in results if q.status == status]
        results.sort(key=lambda q: q.created_at, reverse=True)
        return results

    def send(self, quote_id: str) -> Quote:
        quote = self.get(quote_id)
        quote.status = QuoteStatus.SENT
        quote.sent_at = datetime.now(tz=None).isoformat()
        logger.info("Quote sent: id=%s", quote_id)
        return quote

    def mark_viewed(self, quote_id: str) -> Quote:
        quote = self.get(quote_id)
        quote.status = QuoteStatus.VIEWED
        quote.viewed_at = datetime.now(tz=None).isoformat()
        logger.info("Quote viewed: id=%s", quote_id)
        return quote

    def accept(self, quote_id: str) -> Quote:
        quote = self.get(quote_id)
        quote.status = QuoteStatus.ACCEPTED
        quote.accepted_at = datetime.now(tz=None).isoformat()
        logger.info("Quote accepted: id=%s total=%.2f", quote_id, quote.total)
        return quote

    def reject(self, quote_id: str) -> Quote:
        quote = self.get(quote_id)
        quote.status = QuoteStatus.REJECTED
        logger.info("Quote rejected: id=%s", quote_id)
        return quote

    def duplicate(self, quote_id: str) -> Quote:
        original = self.get(quote_id)
        now = datetime.now(tz=None)
        new_items = [
            LineItem(
                id=str(uuid.uuid4()),
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_percent=item.discount_percent,
                tax_percent=item.tax_percent,
            )
            for item in original.line_items
        ]
        new_quote = Quote(
            id=str(uuid.uuid4()),
            tenant_id=original.tenant_id,
            deal_id=original.deal_id,
            quote_number=self._next_number(),
            title=original.title,
            client_name=original.client_name,
            client_email=original.client_email,
            line_items=new_items,
            subtotal=original.subtotal,
            discount_total=original.discount_total,
            tax_total=original.tax_total,
            total=original.total,
            currency=original.currency,
            status=QuoteStatus.DRAFT,
            valid_until=(now + timedelta(days=30)).isoformat(),
            notes=original.notes,
            terms=original.terms,
            created_by=original.created_by,
            created_at=now.isoformat(),
        )
        self._quotes[new_quote.id] = new_quote
        logger.info("Quote duplicated: %s -> %s", quote_id, new_quote.id)
        return new_quote

    def export_markdown(self, quote_id: str) -> str:
        q = self.get(quote_id)
        lines = [
            f"# Quote {q.quote_number}",
            "",
            f"**{q.title}**",
            "",
            f"- **Client:** {q.client_name} ({q.client_email})",
            f"- **Date:** {q.created_at[:10]}",
            f"- **Valid Until:** {q.valid_until[:10]}",
            f"- **Status:** {q.status.value}",
            "",
            "## Line Items",
            "",
            "| # | Description | Qty | Unit Price | Discount | Tax | Total |",
            "|---|-------------|-----|-----------|----------|-----|-------|",
        ]
        for i, item in enumerate(q.line_items, 1):
            lines.append(
                f"| {i} | {item.description} | {item.quantity} | "
                f"{item.unit_price:.2f} | {item.discount_percent}% | "
                f"{item.tax_percent}% | {item.total:.2f} |"
            )
        lines.extend([
            "",
            f"- **Subtotal:** {q.currency} {q.subtotal:.2f}",
            f"- **Discount:** {q.currency} {q.discount_total:.2f}",
            f"- **Tax:** {q.currency} {q.tax_total:.2f}",
            f"- **Total:** {q.currency} {q.total:.2f}",
        ])
        if q.notes:
            lines.extend(["", "## Notes", "", q.notes])
        if q.terms:
            lines.extend(["", "## Terms", "", q.terms])
        lines.extend(["", "---", f"*Quote {q.quote_number} — Generated by XcapitSFF*"])
        return "\n".join(lines)

    def add_line_item(
        self,
        quote_id: str,
        description: str,
        quantity: float,
        unit_price: float,
        discount_percent: float = 0.0,
        tax_percent: float = 0.0,
    ) -> Quote:
        quote = self.get(quote_id)
        item = LineItem(
            id=str(uuid.uuid4()),
            description=description,
            quantity=quantity,
            unit_price=unit_price,
            discount_percent=discount_percent,
            tax_percent=tax_percent,
        )
        quote.line_items.append(item)
        self._recalculate(quote)
        logger.info("Line item added to quote %s: %s", quote_id, description)
        return quote

    def remove_line_item(self, quote_id: str, item_id: str) -> Quote:
        quote = self.get(quote_id)
        quote.line_items = [li for li in quote.line_items if li.id != item_id]
        self._recalculate(quote)
        logger.info("Line item %s removed from quote %s", item_id, quote_id)
        return quote

    def get_quote_stats(self, tenant_id: str) -> dict:
        quotes = [q for q in self._quotes.values() if q.tenant_id == tenant_id]
        total_sent = len([q for q in quotes if q.status in (
            QuoteStatus.SENT, QuoteStatus.VIEWED, QuoteStatus.ACCEPTED, QuoteStatus.REJECTED,
        )])
        total_accepted = len([q for q in quotes if q.status == QuoteStatus.ACCEPTED])
        acceptance_rate = (total_accepted / total_sent * 100) if total_sent > 0 else 0.0
        total_value_sent = sum(
            q.total for q in quotes if q.status in (
                QuoteStatus.SENT, QuoteStatus.VIEWED, QuoteStatus.ACCEPTED, QuoteStatus.REJECTED,
            )
        )
        total_value_accepted = sum(
            q.total for q in quotes if q.status == QuoteStatus.ACCEPTED
        )
        return {
            "total_sent": total_sent,
            "total_accepted": total_accepted,
            "acceptance_rate": round(acceptance_rate, 1),
            "total_value_sent": round(total_value_sent, 2),
            "total_value_accepted": round(total_value_accepted, 2),
        }


# Singleton
quote_manager = QuoteManager()

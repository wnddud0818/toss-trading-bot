from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from sqlalchemy import Date, DateTime, Numeric, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .models import OrderRequest, OrderResult, OrderSide, Position, UniverseCandidate


class Base(DeclarativeBase):
    pass


class UniverseRow(Base):
    __tablename__ = "universe"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    as_of: Mapped[date] = mapped_column(Date, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(128))
    market: Mapped[str] = mapped_column(String(16))
    trading_value: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    close: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    volume: Mapped[Decimal] = mapped_column(Numeric(20, 4))


class PaperPositionRow(Base):
    __tablename__ = "paper_positions"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    entry_date: Mapped[date] = mapped_column(Date)
    high_watermark: Mapped[Decimal] = mapped_column(Numeric(20, 4))


class PaperCashRow(Base):
    __tablename__ = "paper_cash"

    key: Mapped[str] = mapped_column(String(16), primary_key=True, default="KRW")
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 4))


class TradeRow(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    mode: Mapped[str] = mapped_column(String(16), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    side: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    price: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    commission: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    tax: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    reason: Mapped[str] = mapped_column(String(256), default="")


class EquityRow(Base):
    __tablename__ = "equity_curve"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    equity: Mapped[Decimal] = mapped_column(Numeric(20, 4))


class OrderAuditRow(Base):
    __tablename__ = "order_audit"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    mode: Mapped[str] = mapped_column(String(16), index=True)
    order_id: Mapped[str] = mapped_column(String(160), index=True)
    client_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    side: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    average_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    reason: Mapped[str] = mapped_column(String(256), default="")


def make_engine(database_url: str):
    if database_url.startswith("sqlite:///"):
        db_path = Path(database_url.replace("sqlite:///", "", 1))
        if db_path.parent != Path("."):
            db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(database_url, future=True)


def init_db(database_url: str) -> sessionmaker[Session]:
    engine = make_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False, future=True)


class BotRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    def save_universe(self, as_of: date, candidates: Iterable[UniverseCandidate]) -> None:
        with self.session_factory() as session:
            session.query(UniverseRow).filter(UniverseRow.as_of == as_of).delete()
            for candidate in candidates:
                session.add(
                    UniverseRow(
                        as_of=as_of,
                        symbol=candidate.symbol,
                        name=candidate.name,
                        market=candidate.market,
                        trading_value=candidate.trading_value,
                        close=candidate.close,
                        volume=candidate.volume,
                    )
                )
            session.commit()

    def load_universe(self, as_of: date) -> list[UniverseCandidate]:
        with self.session_factory() as session:
            rows = session.scalars(select(UniverseRow).where(UniverseRow.as_of == as_of)).all()
            return [
                UniverseCandidate(
                    symbol=row.symbol,
                    name=row.name,
                    market=row.market,
                    trading_value=row.trading_value,
                    close=row.close,
                    volume=row.volume,
                )
                for row in rows
            ]

    def load_latest_universe(self) -> list[UniverseCandidate]:
        with self.session_factory() as session:
            latest = session.scalar(select(UniverseRow.as_of).order_by(UniverseRow.as_of.desc()).limit(1))
            if latest is None:
                return []
            rows = session.scalars(select(UniverseRow).where(UniverseRow.as_of == latest)).all()
            return [
                UniverseCandidate(row.symbol, row.name, row.market, row.trading_value, row.close, row.volume)
                for row in rows
            ]

    def upsert_position(self, position: Position) -> None:
        with self.session_factory() as session:
            row = session.get(PaperPositionRow, position.symbol)
            if row is None:
                row = PaperPositionRow(
                    symbol=position.symbol,
                    quantity=position.quantity,
                    entry_price=position.entry_price,
                    entry_date=position.entry_date,
                    high_watermark=position.high_watermark,
                )
                session.add(row)
            else:
                row.quantity = position.quantity
                row.entry_price = position.entry_price
                row.entry_date = position.entry_date
                row.high_watermark = position.high_watermark
            session.commit()

    def delete_position(self, symbol: str) -> None:
        with self.session_factory() as session:
            row = session.get(PaperPositionRow, symbol)
            if row is not None:
                session.delete(row)
            session.commit()

    def list_positions(self) -> list[Position]:
        with self.session_factory() as session:
            rows = session.scalars(select(PaperPositionRow)).all()
            return [
                Position(row.symbol, row.quantity, row.entry_price, row.entry_date, row.high_watermark)
                for row in rows
            ]

    def get_cash(self, initial_cash: Decimal) -> Decimal:
        with self.session_factory() as session:
            row = session.get(PaperCashRow, "KRW")
            if row is None:
                row = PaperCashRow(key="KRW", cash=initial_cash)
                session.add(row)
                session.commit()
            return row.cash

    def set_cash(self, cash: Decimal) -> None:
        with self.session_factory() as session:
            row = session.get(PaperCashRow, "KRW")
            if row is None:
                row = PaperCashRow(key="KRW", cash=cash)
                session.add(row)
            else:
                row.cash = cash
            session.commit()

    def record_trade(
        self,
        ts: datetime,
        mode: str,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        commission: Decimal,
        tax: Decimal,
        reason: str = "",
    ) -> None:
        with self.session_factory() as session:
            session.add(
                TradeRow(
                    ts=ts,
                    mode=mode,
                    symbol=symbol,
                    side=side.value,
                    quantity=quantity,
                    price=price,
                    commission=commission,
                    tax=tax,
                    reason=reason,
                )
            )
            session.commit()

    def record_equity(self, ts: datetime, equity: Decimal) -> None:
        with self.session_factory() as session:
            session.merge(EquityRow(ts=ts, equity=equity))
            session.commit()

    def record_order(
        self,
        ts: datetime,
        mode: str,
        order: OrderRequest,
        result: OrderResult,
        reason: str = "",
    ) -> None:
        with self.session_factory() as session:
            session.add(
                OrderAuditRow(
                    ts=ts,
                    mode=mode,
                    order_id=result.order_id,
                    client_order_id=result.client_order_id,
                    symbol=order.symbol,
                    side=order.side.value,
                    status=result.status,
                    quantity=order.quantity,
                    price=order.price,
                    filled_quantity=result.filled_quantity,
                    average_price=result.average_price,
                    reason=reason,
                )
            )
            session.commit()

    def latest_trades(self, limit: int = 200) -> list[TradeRow]:
        with self.session_factory() as session:
            return list(session.scalars(select(TradeRow).order_by(TradeRow.ts.desc()).limit(limit)).all())

    def latest_order_audits(self, limit: int = 200) -> list[OrderAuditRow]:
        with self.session_factory() as session:
            return list(session.scalars(select(OrderAuditRow).order_by(OrderAuditRow.ts.desc()).limit(limit)).all())

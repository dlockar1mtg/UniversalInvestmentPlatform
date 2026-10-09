"""Immutable manual performance snapshots for external accounts."""
from __future__ import annotations
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib, json, math, re, sqlite3
from typing import Callable, Mapping, Protocol, Sequence

# Account kinds tracked by manual snapshot: kind -> (label, category). Retirement accounts are entered from each
# statement (balance, and contributions to date when the statement shows them). A person can hold several
# accounts of one kind, so an account id is the kind alone or "kind:name-slug" (e.g. "retirement-401k:plan-a").
KINDS = {"acorns": ("Acorns", "brokerage"), "retirement-401k": ("401(k) / 403(b)", "retirement"),
         "ira": ("IRA", "retirement"), "hsa": ("HSA", "retirement"), "pension": ("Pension", "retirement")}
ACCOUNTS = KINDS
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


def kind_of(account_id: str) -> str:
    """The account's kind; raises ValueError for an id outside the registry."""
    kind, _, slug = str(account_id).partition(":")
    if kind not in KINDS or (slug and (kind == "acorns" or not _SLUG.fullmatch(slug))) or (not slug and ":" in str(account_id)):
        raise ValueError(f"unknown account: {account_id}")
    return kind


def paychecks_between(after: date, through: date, next_paycheck: date, every_days: int) -> int:
    """Paydays on the schedule (every `every_days` days, one of them on `next_paycheck`) in (after, through]."""
    if through <= after:
        return 0
    lo = math.ceil(((after - next_paycheck).days + 1) / every_days)
    hi = math.floor((through - next_paycheck).days / every_days)
    return max(0, hi - lo + 1)


def estimate(item: "ExternalAccountPerformance", schedule: Mapping | None, today: date) -> dict:
    """Balance today: the last statement plus paycheck deposits since (no market change is assumed)."""
    out = {"as_of_date": today.isoformat(), "paychecks_since": 0, "value": str(item.current_value),
           "basis": str(item.contributed_basis) if item.basis_known else None, "method": "STATEMENT"}
    if not schedule:
        return out
    n = paychecks_between(item.as_of.date(), today, date.fromisoformat(str(schedule["next_paycheck"])), int(schedule["every_days"]))
    add = Decimal(str(schedule["per_paycheck"])) * n
    out.update(paychecks_since=n, value=str(item.current_value + add),
               basis=str(item.contributed_basis + add) if item.basis_known else None,
               method="STATEMENT_PLUS_PAYCHECKS" if n else "STATEMENT")
    return out


def monthly_equivalent(per_paycheck, every_days) -> str:
    return str((Decimal(str(per_paycheck)) * Decimal("365.25") / Decimal(int(every_days)) / 12).quantize(Decimal("0.01"), ROUND_HALF_UP))


def validate_schedule(per_paycheck, every_days, next_paycheck) -> dict:
    amount = Decimal(str(per_paycheck))
    if not amount.is_finite() or amount <= 0 or amount > Decimal("100000"):
        raise ValueError("per_paycheck must be a positive amount")
    days = int(every_days)
    if not 7 <= days <= 31:
        raise ValueError("every_days must be between 7 and 31")
    when = date.fromisoformat(str(next_paycheck)[:10])
    return {"per_paycheck": str(amount), "every_days": days, "next_paycheck": when.isoformat()}

@dataclass(frozen=True)
class ExternalAccountPerformance:
    snapshot_id: str
    fingerprint: str
    account_id: str
    provider: str
    as_of: datetime
    current_value: Decimal
    contributed_basis: Decimal
    recorded_at: datetime
    recorded_by: str
    notes: str = ""
    authority_state: str = "MANUAL_USER_ENTERED_EXTERNAL_ACCOUNT_PERFORMANCE"
    def __post_init__(self):
        kind_of(self.account_id)
        if self.account_id == "acorns" and self.provider != "Acorns": raise ValueError("the Acorns account's provider is Acorns")
        if not self.provider.strip() or len(self.provider) > 80 or not self.provider.isprintable(): raise ValueError("provider must be 1-80 printable characters")
        if self.as_of.tzinfo is None or self.recorded_at.tzinfo is None: raise ValueError("timestamps must be timezone-aware")
        if self.current_value < 0 or self.contributed_basis < 0: raise ValueError("values must be non-negative")
    @property
    def basis_known(self): return self.account_id == "acorns" or self.contributed_basis > 0
    @property
    def kind(self): return kind_of(self.account_id)
    @property
    def gain_loss(self): return self.current_value - self.contributed_basis if self.basis_known else None
    @property
    def return_pct(self): return None if self.contributed_basis == 0 or self.gain_loss is None else self.gain_loss / self.contributed_basis * Decimal(100)
    def document(self):
        return {"snapshot_id":self.snapshot_id,"fingerprint":self.fingerprint,"account_id":self.account_id,"provider":self.provider,"as_of":self.as_of.isoformat(),"current_value":str(self.current_value),"contributed_basis":str(self.contributed_basis),"account_kind":self.kind,"account_label":KINDS[self.kind][0],"category":KINDS[self.kind][1],"basis_known":self.basis_known,"gain_loss":None if self.gain_loss is None else str(self.gain_loss),"return_pct":None if self.return_pct is None else str(self.return_pct),"recorded_at":self.recorded_at.isoformat(),"recorded_by":self.recorded_by,"notes":self.notes,"authority_state":self.authority_state}

class ExternalAccountPerformanceRepository(Protocol):
    def initialize(self)->None: ...
    def save(self,item:ExternalAccountPerformance)->ExternalAccountPerformance: ...
    def latest(self,account_id:str="acorns")->ExternalAccountPerformance|None: ...
    def history(self,account_id:str="acorns",limit:int=20)->tuple[ExternalAccountPerformance,...]: ...
    def accounts(self)->tuple[str,...]: ...
    def schedules(self)->dict[str,dict]: ...
    def save_schedule(self,account_id:str,schedule:dict|None,updated_by:str)->None: ...

def create_snapshot(*, account_id:str, provider:str, as_of:datetime, current_value:Decimal, contributed_basis:Decimal, recorded_by:str, notes:str="", recorded_at:datetime|None=None)->ExternalAccountPerformance:
    if as_of.tzinfo is None: raise ValueError("as_of must include timezone")
    now=recorded_at or datetime.now(timezone.utc)
    payload={"account_id":account_id,"provider":provider,"as_of":as_of.isoformat(),"current_value":str(current_value),"contributed_basis":str(contributed_basis),"notes":notes}
    fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
    return ExternalAccountPerformance(f"external-{fingerprint[:24]}",fingerprint,account_id,provider,as_of,current_value,contributed_basis,now,recorded_by,notes)

_SCHEDULE_SQL="CREATE TABLE IF NOT EXISTS external_account_schedules (account_id TEXT PRIMARY KEY,per_paycheck TEXT NOT NULL,every_days INTEGER NOT NULL,next_paycheck TEXT NOT NULL,updated_at TEXT NOT NULL,updated_by TEXT NOT NULL)"
_SCHEDULE_SQL_PG="CREATE TABLE IF NOT EXISTS external_account_schedules (account_id TEXT PRIMARY KEY,per_paycheck NUMERIC NOT NULL CHECK(per_paycheck>0),every_days INTEGER NOT NULL CHECK(every_days BETWEEN 7 AND 31),next_paycheck DATE NOT NULL,updated_at TIMESTAMPTZ NOT NULL,updated_by TEXT NOT NULL)"
_COLS=("snapshot_id","fingerprint","account_id","provider","as_of","current_value","contributed_basis","recorded_at","recorded_by","notes","authority_state")
def _hydrate(row:Sequence[object])->ExternalAccountPerformance:
    return ExternalAccountPerformance(str(row[0]),str(row[1]),str(row[2]),str(row[3]),row[4] if isinstance(row[4],datetime) else datetime.fromisoformat(str(row[4])),Decimal(str(row[5])),Decimal(str(row[6])),row[7] if isinstance(row[7],datetime) else datetime.fromisoformat(str(row[7])),str(row[8]),str(row[9]),str(row[10]))
class SQLiteExternalAccountPerformanceRepository:
    def __init__(self,connection:sqlite3.Connection): self._db=connection
    def initialize(self):
        self._db.execute("CREATE TABLE IF NOT EXISTS external_account_performance (snapshot_id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL UNIQUE,account_id TEXT NOT NULL,provider TEXT NOT NULL,as_of TEXT NOT NULL,current_value TEXT NOT NULL,contributed_basis TEXT NOT NULL,recorded_at TEXT NOT NULL,recorded_by TEXT NOT NULL,notes TEXT NOT NULL,authority_state TEXT NOT NULL)"); self._db.execute("CREATE INDEX IF NOT EXISTS external_account_performance_idx ON external_account_performance(account_id,recorded_at DESC)"); self._db.execute(_SCHEDULE_SQL); self._db.commit()
    def save(self,item):
        row=self._db.execute("SELECT snapshot_id FROM external_account_performance WHERE fingerprint=?",(item.fingerprint,)).fetchone()
        if row:return self.get(row[0])
        with self._db:self._db.execute("INSERT INTO external_account_performance VALUES (?,?,?,?,?,?,?,?,?,?,?)",tuple(v.isoformat() if isinstance(v,datetime) else str(v) if isinstance(v,Decimal) else v for v in (item.snapshot_id,item.fingerprint,item.account_id,item.provider,item.as_of,item.current_value,item.contributed_basis,item.recorded_at,item.recorded_by,item.notes,item.authority_state)))
        return item
    def get(self,snapshot_id):
        row=self._db.execute("SELECT "+",".join(_COLS)+" FROM external_account_performance WHERE snapshot_id=?",(snapshot_id,)).fetchone()
        if row is None: raise KeyError(snapshot_id)
        return _hydrate(row)
    def latest(self,account_id="acorns"):
        row=self._db.execute("SELECT "+",".join(_COLS)+" FROM external_account_performance WHERE account_id=? ORDER BY as_of DESC,recorded_at DESC,snapshot_id DESC LIMIT 1",(account_id,)).fetchone(); return None if row is None else _hydrate(row)
    def accounts(self): return tuple(r[0] for r in self._db.execute("SELECT DISTINCT account_id FROM external_account_performance ORDER BY account_id").fetchall())
    def schedules(self): return {r[0]:{"per_paycheck":str(r[1]),"every_days":int(r[2]),"next_paycheck":str(r[3])[:10],"updated_at":str(r[4])} for r in self._db.execute("SELECT account_id,per_paycheck,every_days,next_paycheck,updated_at FROM external_account_schedules").fetchall()}
    def save_schedule(self,account_id,schedule,updated_by):
        with self._db:
            if schedule is None: self._db.execute("DELETE FROM external_account_schedules WHERE account_id=?",(account_id,)); return
            self._db.execute("INSERT INTO external_account_schedules VALUES (?,?,?,?,?,?) ON CONFLICT(account_id) DO UPDATE SET per_paycheck=excluded.per_paycheck,every_days=excluded.every_days,next_paycheck=excluded.next_paycheck,updated_at=excluded.updated_at,updated_by=excluded.updated_by",(account_id,schedule["per_paycheck"],schedule["every_days"],schedule["next_paycheck"],datetime.now(timezone.utc).isoformat(),updated_by))
    def history(self,account_id="acorns",limit=20):
        if not 1<=limit<=100: raise ValueError("history limit must be between 1 and 100")
        return tuple(_hydrate(r) for r in self._db.execute("SELECT "+",".join(_COLS)+" FROM external_account_performance WHERE account_id=? ORDER BY as_of DESC,recorded_at DESC,snapshot_id DESC LIMIT ?",(account_id,limit)).fetchall())
class PostgresExternalAccountPerformanceRepository:
    def __init__(self,connection_factory:Callable[[],object]): self._connection_factory=connection_factory
    @classmethod
    def from_dsn(cls,dsn):
        if not dsn.strip(): raise ValueError("PostgreSQL DSN must not be blank")
        import psycopg
        return cls(lambda:psycopg.connect(dsn))
    def initialize(self):
        with closing(self._connection_factory()) as db,db,db.cursor() as c:
            c.execute("CREATE TABLE IF NOT EXISTS external_account_performance (snapshot_id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL UNIQUE,account_id TEXT NOT NULL,provider TEXT NOT NULL,as_of TIMESTAMPTZ NOT NULL,current_value NUMERIC NOT NULL CHECK(current_value>=0),contributed_basis NUMERIC NOT NULL CHECK(contributed_basis>=0),recorded_at TIMESTAMPTZ NOT NULL,recorded_by TEXT NOT NULL,notes TEXT NOT NULL,authority_state TEXT NOT NULL)"); c.execute("CREATE INDEX IF NOT EXISTS external_account_performance_idx ON external_account_performance(account_id,as_of DESC,recorded_at DESC)"); c.execute(_SCHEDULE_SQL_PG)
    def save(self,item):
        with closing(self._connection_factory()) as db,db,db.cursor() as c:
            c.execute("SELECT "+",".join(_COLS)+" FROM external_account_performance WHERE fingerprint=%s",(item.fingerprint,)); row=c.fetchone()
            if row:return _hydrate(row)
            c.execute("INSERT INTO external_account_performance VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(item.snapshot_id,item.fingerprint,item.account_id,item.provider,item.as_of,item.current_value,item.contributed_basis,item.recorded_at,item.recorded_by,item.notes,item.authority_state))
        return item
    def accounts(self):
        with closing(self._connection_factory()) as db,db.cursor() as c:c.execute("SELECT DISTINCT account_id FROM external_account_performance ORDER BY account_id"); return tuple(r[0] for r in c.fetchall())
    def schedules(self):
        with closing(self._connection_factory()) as db,db.cursor() as c:c.execute("SELECT account_id,per_paycheck,every_days,next_paycheck,updated_at FROM external_account_schedules"); rows=c.fetchall()
        return {r[0]:{"per_paycheck":str(r[1]),"every_days":int(r[2]),"next_paycheck":str(r[3])[:10],"updated_at":str(r[4])} for r in rows}
    def save_schedule(self,account_id,schedule,updated_by):
        with closing(self._connection_factory()) as db,db,db.cursor() as c:
            if schedule is None: c.execute("DELETE FROM external_account_schedules WHERE account_id=%s",(account_id,)); return
            c.execute("INSERT INTO external_account_schedules VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(account_id) DO UPDATE SET per_paycheck=EXCLUDED.per_paycheck,every_days=EXCLUDED.every_days,next_paycheck=EXCLUDED.next_paycheck,updated_at=EXCLUDED.updated_at,updated_by=EXCLUDED.updated_by",(account_id,Decimal(schedule["per_paycheck"]),schedule["every_days"],schedule["next_paycheck"],datetime.now(timezone.utc),updated_by))
    def latest(self,account_id="acorns"): return self._one("WHERE account_id=%s ORDER BY as_of DESC,recorded_at DESC,snapshot_id DESC LIMIT 1",(account_id,))
    def history(self,account_id="acorns",limit=20):
        if not 1<=limit<=100: raise ValueError("history limit must be between 1 and 100")
        with closing(self._connection_factory()) as db,db.cursor() as c:c.execute("SELECT "+",".join(_COLS)+" FROM external_account_performance WHERE account_id=%s ORDER BY as_of DESC,recorded_at DESC,snapshot_id DESC LIMIT %s",(account_id,limit)); rows=c.fetchall()
        return tuple(_hydrate(r) for r in rows)
    def _one(self,clause,args):
        with closing(self._connection_factory()) as db,db.cursor() as c:c.execute("SELECT "+",".join(_COLS)+" FROM external_account_performance "+clause,args); row=c.fetchone()
        return None if row is None else _hydrate(row)

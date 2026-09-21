"""Immutable manual performance snapshots for external accounts."""
from __future__ import annotations
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib, json, sqlite3
from typing import Callable, Mapping, Protocol, Sequence

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
        if self.account_id != "acorns" or self.provider != "Acorns": raise ValueError("only the Acorns account is supported")
        if self.as_of.tzinfo is None or self.recorded_at.tzinfo is None: raise ValueError("timestamps must be timezone-aware")
        if self.current_value < 0 or self.contributed_basis < 0: raise ValueError("values must be non-negative")
    @property
    def gain_loss(self): return self.current_value - self.contributed_basis
    @property
    def return_pct(self): return None if self.contributed_basis == 0 else self.gain_loss / self.contributed_basis * Decimal(100)
    def document(self):
        return {"snapshot_id":self.snapshot_id,"fingerprint":self.fingerprint,"account_id":self.account_id,"provider":self.provider,"as_of":self.as_of.isoformat(),"current_value":str(self.current_value),"contributed_basis":str(self.contributed_basis),"gain_loss":str(self.gain_loss),"return_pct":None if self.return_pct is None else str(self.return_pct),"recorded_at":self.recorded_at.isoformat(),"recorded_by":self.recorded_by,"notes":self.notes,"authority_state":self.authority_state}

class ExternalAccountPerformanceRepository(Protocol):
    def initialize(self)->None: ...
    def save(self,item:ExternalAccountPerformance)->ExternalAccountPerformance: ...
    def latest(self,account_id:str="acorns")->ExternalAccountPerformance|None: ...
    def history(self,account_id:str="acorns",limit:int=20)->tuple[ExternalAccountPerformance,...]: ...

def create_snapshot(*, account_id:str, provider:str, as_of:datetime, current_value:Decimal, contributed_basis:Decimal, recorded_by:str, notes:str="", recorded_at:datetime|None=None)->ExternalAccountPerformance:
    if as_of.tzinfo is None: raise ValueError("as_of must include timezone")
    now=recorded_at or datetime.now(timezone.utc)
    payload={"account_id":account_id,"provider":provider,"as_of":as_of.isoformat(),"current_value":str(current_value),"contributed_basis":str(contributed_basis),"notes":notes}
    fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
    return ExternalAccountPerformance(f"external-{fingerprint[:24]}",fingerprint,account_id,provider,as_of,current_value,contributed_basis,now,recorded_by,notes)

_COLS=("snapshot_id","fingerprint","account_id","provider","as_of","current_value","contributed_basis","recorded_at","recorded_by","notes","authority_state")
def _hydrate(row:Sequence[object])->ExternalAccountPerformance:
    return ExternalAccountPerformance(str(row[0]),str(row[1]),str(row[2]),str(row[3]),row[4] if isinstance(row[4],datetime) else datetime.fromisoformat(str(row[4])),Decimal(str(row[5])),Decimal(str(row[6])),row[7] if isinstance(row[7],datetime) else datetime.fromisoformat(str(row[7])),str(row[8]),str(row[9]),str(row[10]))
class SQLiteExternalAccountPerformanceRepository:
    def __init__(self,connection:sqlite3.Connection): self._db=connection
    def initialize(self):
        self._db.execute("CREATE TABLE IF NOT EXISTS external_account_performance (snapshot_id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL UNIQUE,account_id TEXT NOT NULL,provider TEXT NOT NULL,as_of TEXT NOT NULL,current_value TEXT NOT NULL,contributed_basis TEXT NOT NULL,recorded_at TEXT NOT NULL,recorded_by TEXT NOT NULL,notes TEXT NOT NULL,authority_state TEXT NOT NULL)"); self._db.execute("CREATE INDEX IF NOT EXISTS external_account_performance_idx ON external_account_performance(account_id,recorded_at DESC)"); self._db.commit()
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
            c.execute("CREATE TABLE IF NOT EXISTS external_account_performance (snapshot_id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL UNIQUE,account_id TEXT NOT NULL,provider TEXT NOT NULL,as_of TIMESTAMPTZ NOT NULL,current_value NUMERIC NOT NULL CHECK(current_value>=0),contributed_basis NUMERIC NOT NULL CHECK(contributed_basis>=0),recorded_at TIMESTAMPTZ NOT NULL,recorded_by TEXT NOT NULL,notes TEXT NOT NULL,authority_state TEXT NOT NULL)"); c.execute("CREATE INDEX IF NOT EXISTS external_account_performance_idx ON external_account_performance(account_id,as_of DESC,recorded_at DESC)")
    def save(self,item):
        with closing(self._connection_factory()) as db,db,db.cursor() as c:
            c.execute("SELECT "+",".join(_COLS)+" FROM external_account_performance WHERE fingerprint=%s",(item.fingerprint,)); row=c.fetchone()
            if row:return _hydrate(row)
            c.execute("INSERT INTO external_account_performance VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(item.snapshot_id,item.fingerprint,item.account_id,item.provider,item.as_of,item.current_value,item.contributed_basis,item.recorded_at,item.recorded_by,item.notes,item.authority_state))
        return item
    def latest(self,account_id="acorns"): return self._one("WHERE account_id=%s ORDER BY as_of DESC,recorded_at DESC,snapshot_id DESC LIMIT 1",(account_id,))
    def history(self,account_id="acorns",limit=20):
        if not 1<=limit<=100: raise ValueError("history limit must be between 1 and 100")
        with closing(self._connection_factory()) as db,db.cursor() as c:c.execute("SELECT "+",".join(_COLS)+" FROM external_account_performance WHERE account_id=%s ORDER BY as_of DESC,recorded_at DESC,snapshot_id DESC LIMIT %s",(account_id,limit)); rows=c.fetchall()
        return tuple(_hydrate(r) for r in rows)
    def _one(self,clause,args):
        with closing(self._connection_factory()) as db,db.cursor() as c:c.execute("SELECT "+",".join(_COLS)+" FROM external_account_performance "+clause,args); row=c.fetchone()
        return None if row is None else _hydrate(row)

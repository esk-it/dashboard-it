"""
Router Bastion — Gestionnaire de connexions SSH / RDP.
CRUD serveurs + groupes, TCP ping, WebSocket SSH terminal.
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
import socket
import subprocess
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from ..schemas.bastion import (
    GroupCreate, GroupUpdate, GroupResponse,
    ServerCreate, ServerUpdate, ServerResponse,
    PingResult, PingRequest, BastionStats,
)

router = APIRouter(prefix="/api/bastion", tags=["bastion"])

# ── Database ──────────────────────────────────────────────────────────────────

from ..database import DB_PATH
OLD_DB_PATH = Path(r"C:\Users\jdeniel\Documents\Projets\Dashboard - claude code\dashboard.db")

_DEFAULT_GROUPS = [
    ("Production", "#EF4444", 0),
    ("Développement", "#F59E0B", 1),
    ("Réseau", "#10B981", 2),
    ("Sécurité", "#8B5CF6", 3),
    ("Windows", "#3B82F6", 4),
    ("Linux", "#06B6D4", 5),
]


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _get_db():
    """Return a raw sqlite3 connection."""
    import sqlite3
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def _init_bastion_tables():
    """Create bastion tables if they don't exist, seed defaults."""
    con = _get_db()
    try:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS bastion_groups (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL UNIQUE,
                color_hex  TEXT    NOT NULL DEFAULT '#4B8BFF',
                sort_order INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS bastion_servers (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT    NOT NULL,
                hostname     TEXT    NOT NULL,
                port         INTEGER NOT NULL DEFAULT 22,
                username     TEXT    NOT NULL DEFAULT '',
                protocol     TEXT    NOT NULL DEFAULT 'SSH',
                group_name   TEXT    NOT NULL DEFAULT '',
                notes        TEXT    NOT NULL DEFAULT '',
                ssh_key_path TEXT    NOT NULL DEFAULT '',
                created_at   TEXT    NOT NULL DEFAULT '',
                updated_at   TEXT    NOT NULL DEFAULT ''
            );
        """)
        # Seed default groups if empty
        count = con.execute("SELECT COUNT(*) FROM bastion_groups").fetchone()[0]
        if count == 0:
            for name, color, order in _DEFAULT_GROUPS:
                con.execute(
                    "INSERT INTO bastion_groups (name, color_hex, sort_order) VALUES (?,?,?)",
                    (name, color, order),
                )
        # If old DB has bastion data and ours is empty, copy it
        if OLD_DB_PATH.exists():
            srv_count = con.execute("SELECT COUNT(*) FROM bastion_servers").fetchone()[0]
            if srv_count == 0:
                import sqlite3 as sq
                old_con = sq.connect(str(OLD_DB_PATH))
                old_con.row_factory = sq.Row
                # Check if old DB has bastion tables
                tbl = old_con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='bastion_servers'"
                ).fetchone()
                if tbl:
                    rows = old_con.execute("SELECT * FROM bastion_servers").fetchall()
                    for r in rows:
                        keys = r.keys()
                        con.execute(
                            "INSERT INTO bastion_servers "
                            "(name,hostname,port,username,protocol,group_name,notes,ssh_key_path,created_at,updated_at) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (
                                r["name"], r["hostname"], r["port"],
                                r["username"] or "", r["protocol"] or "SSH",
                                r["group_name"] or "", r["notes"] if "notes" in keys else "",
                                r["ssh_key_path"] if "ssh_key_path" in keys else "",
                                r["created_at"] or "", r["updated_at"] or "",
                            ),
                        )
                    # Also copy groups
                    old_groups = old_con.execute("SELECT * FROM bastion_groups").fetchall()
                    if old_groups:
                        con.execute("DELETE FROM bastion_groups")
                        for g in old_groups:
                            con.execute(
                                "INSERT INTO bastion_groups (name, color_hex, sort_order) VALUES (?,?,?)",
                                (g["name"], g["color_hex"], g["sort_order"]),
                            )
                old_con.close()
        con.commit()
    finally:
        con.close()


# Initialize tables on module load
_init_bastion_tables()


# ── Groups CRUD ───────────────────────────────────────────────────────────────

@router.get("/groups", response_model=list[GroupResponse])
async def list_groups():
    con = _get_db()
    try:
        groups = con.execute("SELECT * FROM bastion_groups ORDER BY sort_order, name").fetchall()
        counts = {}
        for r in con.execute("SELECT group_name, COUNT(*) AS cnt FROM bastion_servers GROUP BY group_name").fetchall():
            counts[r["group_name"]] = r["cnt"]
        return [
            GroupResponse(
                id=g["id"], name=g["name"], color_hex=g["color_hex"],
                sort_order=g["sort_order"], server_count=counts.get(g["name"], 0),
            )
            for g in groups
        ]
    finally:
        con.close()


@router.post("/groups", response_model=GroupResponse)
async def create_group(data: GroupCreate):
    con = _get_db()
    try:
        order = con.execute("SELECT COALESCE(MAX(sort_order),0)+1 FROM bastion_groups").fetchone()[0]
        cur = con.execute(
            "INSERT INTO bastion_groups (name, color_hex, sort_order) VALUES (?,?,?)",
            (data.name.strip(), data.color_hex, order),
        )
        con.commit()
        return GroupResponse(id=cur.lastrowid, name=data.name.strip(),
                             color_hex=data.color_hex, sort_order=order, server_count=0)
    except Exception as e:
        raise HTTPException(400, str(e))
    finally:
        con.close()


@router.put("/groups/{group_id}", response_model=GroupResponse)
async def update_group(group_id: int, data: GroupUpdate):
    con = _get_db()
    try:
        existing = con.execute("SELECT * FROM bastion_groups WHERE id=?", (group_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Group not found")
        old_name = existing["name"]
        new_name = data.name.strip() if data.name else old_name
        new_color = data.color_hex if data.color_hex else existing["color_hex"]
        new_order = data.sort_order if data.sort_order is not None else existing["sort_order"]
        con.execute(
            "UPDATE bastion_groups SET name=?, color_hex=?, sort_order=? WHERE id=?",
            (new_name, new_color, new_order, group_id),
        )
        if new_name != old_name:
            con.execute(
                "UPDATE bastion_servers SET group_name=? WHERE group_name=?",
                (new_name, old_name),
            )
        con.commit()
        cnt = con.execute(
            "SELECT COUNT(*) FROM bastion_servers WHERE group_name=?", (new_name,)
        ).fetchone()[0]
        return GroupResponse(id=group_id, name=new_name, color_hex=new_color,
                             sort_order=new_order, server_count=cnt)
    finally:
        con.close()


@router.delete("/groups/{group_id}")
async def delete_group(group_id: int):
    con = _get_db()
    try:
        g = con.execute("SELECT name FROM bastion_groups WHERE id=?", (group_id,)).fetchone()
        if not g:
            raise HTTPException(404, "Group not found")
        con.execute("DELETE FROM bastion_groups WHERE id=?", (group_id,))
        con.execute("UPDATE bastion_servers SET group_name='' WHERE group_name=?", (g["name"],))
        con.commit()
        return {"ok": True}
    finally:
        con.close()


# ── Servers CRUD ──────────────────────────────────────────────────────────────

@router.get("/servers", response_model=list[ServerResponse])
async def list_servers(
    group: str = Query("", description="Filter by group name"),
    protocol: str = Query("", description="Filter by protocol (SSH/RDP)"),
    search: str = Query("", description="Search name/hostname/username/notes"),
):
    con = _get_db()
    try:
        q = "SELECT * FROM bastion_servers WHERE 1=1"
        params = []
        if group:
            q += " AND group_name=?"
            params.append(group)
        if protocol:
            q += " AND protocol=?"
            params.append(protocol.upper())
        if search:
            like = f"%{search}%"
            q += " AND (name LIKE ? OR hostname LIKE ? OR username LIKE ? OR notes LIKE ?)"
            params += [like, like, like, like]
        q += " ORDER BY name COLLATE NOCASE"
        rows = con.execute(q, params).fetchall()
        return [_row_to_server(r) for r in rows]
    finally:
        con.close()


@router.get("/servers/{server_id}", response_model=ServerResponse)
async def get_server(server_id: int):
    con = _get_db()
    try:
        row = con.execute("SELECT * FROM bastion_servers WHERE id=?", (server_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Server not found")
        return _row_to_server(row)
    finally:
        con.close()


@router.post("/servers", response_model=ServerResponse)
async def create_server(data: ServerCreate):
    now = _now_iso()
    con = _get_db()
    try:
        cur = con.execute(
            "INSERT INTO bastion_servers "
            "(name,hostname,port,username,protocol,group_name,notes,ssh_key_path,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                data.name.strip(), data.hostname.strip(), data.port,
                data.username.strip(), data.protocol.upper(),
                data.group_name, data.notes, data.ssh_key_path, now, now,
            ),
        )
        con.commit()
        row = con.execute("SELECT * FROM bastion_servers WHERE id=?", (cur.lastrowid,)).fetchone()
        return _row_to_server(row)
    finally:
        con.close()


@router.put("/servers/{server_id}", response_model=ServerResponse)
async def update_server(server_id: int, data: ServerUpdate):
    con = _get_db()
    try:
        existing = con.execute("SELECT * FROM bastion_servers WHERE id=?", (server_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Server not found")
        now = _now_iso()
        updates = {}
        for field in ("name", "hostname", "port", "username", "protocol",
                      "group_name", "notes", "ssh_key_path"):
            val = getattr(data, field)
            if val is not None:
                if field in ("name", "hostname", "username"):
                    val = val.strip()
                if field == "protocol":
                    val = val.upper()
                updates[field] = val
        if not updates:
            return _row_to_server(existing)
        updates["updated_at"] = now
        set_clause = ", ".join(f"{k}=?" for k in updates)
        con.execute(
            f"UPDATE bastion_servers SET {set_clause} WHERE id=?",
            list(updates.values()) + [server_id],
        )
        con.commit()
        row = con.execute("SELECT * FROM bastion_servers WHERE id=?", (server_id,)).fetchone()
        return _row_to_server(row)
    finally:
        con.close()


@router.delete("/servers/{server_id}")
async def delete_server(server_id: int):
    con = _get_db()
    try:
        con.execute("DELETE FROM bastion_servers WHERE id=?", (server_id,))
        con.commit()
        return {"ok": True}
    finally:
        con.close()


# ── TCP Ping ──────────────────────────────────────────────────────────────────

@router.post("/ping", response_model=list[PingResult])
async def ping_servers(data: PingRequest):
    con = _get_db()
    try:
        results = []
        for sid in data.server_ids:
            row = con.execute("SELECT hostname, port FROM bastion_servers WHERE id=?", (sid,)).fetchone()
            if not row:
                results.append(PingResult(server_id=sid, alive=False, latency_ms=0))
                continue
            alive, ms = await _tcp_ping(row["hostname"], row["port"])
            results.append(PingResult(server_id=sid, alive=alive, latency_ms=ms))
        return results
    finally:
        con.close()


@router.post("/ping/{server_id}", response_model=PingResult)
async def ping_single(server_id: int):
    con = _get_db()
    try:
        row = con.execute("SELECT hostname, port FROM bastion_servers WHERE id=?", (server_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Server not found")
        alive, ms = await _tcp_ping(row["hostname"], row["port"])
        return PingResult(server_id=server_id, alive=alive, latency_ms=ms)
    finally:
        con.close()


async def _tcp_ping(hostname: str, port: int, timeout: float = 3.0) -> tuple[bool, int]:
    """Test TCP connectivity, return (alive, latency_ms)."""
    loop = asyncio.get_event_loop()
    t0 = time.monotonic()
    try:
        await asyncio.wait_for(
            loop.run_in_executor(None, _sync_tcp_ping, hostname, port, timeout),
            timeout=timeout + 1,
        )
        ms = int((time.monotonic() - t0) * 1000)
        return True, ms
    except Exception:
        return False, 0


def _sync_tcp_ping(hostname: str, port: int, timeout: float):
    with socket.create_connection((hostname, port), timeout=timeout):
        pass


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=BastionStats)
async def get_stats():
    con = _get_db()
    try:
        total = con.execute("SELECT COUNT(*) FROM bastion_servers").fetchone()[0]
        ssh = con.execute("SELECT COUNT(*) FROM bastion_servers WHERE protocol='SSH'").fetchone()[0]
        rdp = con.execute("SELECT COUNT(*) FROM bastion_servers WHERE protocol='RDP'").fetchone()[0]
        grp_count = con.execute("SELECT COUNT(*) FROM bastion_groups").fetchone()[0]
        by_group = {}
        for r in con.execute("SELECT group_name, COUNT(*) AS cnt FROM bastion_servers GROUP BY group_name").fetchall():
            by_group[r["group_name"] or "(sans groupe)"] = r["cnt"]
        return BastionStats(total=total, ssh_count=ssh, rdp_count=rdp,
                            groups_count=grp_count, by_group=by_group)
    finally:
        con.close()


# ── WebSocket SSH Terminal ────────────────────────────────────────────────────

@router.websocket("/ssh/{server_id}")
async def ssh_terminal(ws: WebSocket, server_id: int):
    """WebSocket bridge: browser (xterm.js) <-> paramiko SSH."""
    await ws.accept()

    con = _get_db()
    try:
        row = con.execute("SELECT * FROM bastion_servers WHERE id=?", (server_id,)).fetchone()
        if not row:
            await ws.send_json({"type": "error", "data": "Server not found"})
            await ws.close()
            return
        if row["protocol"].upper() != "SSH":
            await ws.send_json({"type": "error", "data": "Not an SSH server"})
            await ws.close()
            return
        hostname = row["hostname"]
        port = row["port"] or 22
        username = row["username"] or ""
        ssh_key_path = row["ssh_key_path"] or ""
    finally:
        con.close()

    try:
        import paramiko
    except ImportError:
        await ws.send_json({"type": "error", "data": "paramiko not installed on server"})
        await ws.close()
        return

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    channel = None

    try:
        # Connect SSH
        connect_kwargs = dict(
            hostname=hostname, port=port, username=username,
            timeout=10, allow_agent=True, look_for_keys=True,
        )
        if ssh_key_path and Path(ssh_key_path).exists():
            connect_kwargs["key_filename"] = ssh_key_path

        await ws.send_json({"type": "status", "data": "connecting"})

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: client.connect(**connect_kwargs))

        channel = client.invoke_shell(term="xterm-256color", width=80, height=24)
        channel.settimeout(0.0)

        await ws.send_json({"type": "status", "data": "connected"})

        # Read from SSH -> WebSocket
        async def ssh_to_ws():
            while True:
                try:
                    data = await loop.run_in_executor(None, _ssh_recv, channel)
                    if data:
                        await ws.send_json({"type": "data", "data": data})
                    elif data is None:
                        break
                    else:
                        await asyncio.sleep(0.02)
                except Exception:
                    break

        # Read from WebSocket -> SSH
        async def ws_to_ssh():
            while True:
                try:
                    msg = await ws.receive_json()
                    if msg.get("type") == "data":
                        channel.send(msg["data"])
                    elif msg.get("type") == "resize":
                        cols = msg.get("cols", 80)
                        rows = msg.get("rows", 24)
                        channel.resize_pty(width=cols, height=rows)
                except WebSocketDisconnect:
                    break
                except Exception:
                    break

        await asyncio.gather(ssh_to_ws(), ws_to_ssh())

    except paramiko.AuthenticationException:
        await ws.send_json({"type": "error", "data": "Authentication failed. Check SSH key or credentials."})
    except paramiko.SSHException as e:
        await ws.send_json({"type": "error", "data": f"SSH error: {e}"})
    except socket.timeout:
        await ws.send_json({"type": "error", "data": f"Connection timeout to {hostname}:{port}"})
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "data": str(e)})
        except Exception:
            pass
    finally:
        if channel:
            try:
                channel.close()
            except Exception:
                pass
        try:
            client.close()
        except Exception:
            pass
        try:
            await ws.close()
        except Exception:
            pass


def _ssh_recv(channel) -> Optional[str]:
    """Read from SSH channel. Returns data, '' if nothing, None if closed."""
    import paramiko
    if channel.exit_status_ready():
        return None
    if channel.recv_ready():
        return channel.recv(4096).decode("utf-8", errors="replace")
    import time
    time.sleep(0.02)
    return ""


# ── Generate RDP file content ─────────────────────────────────────────────────

@router.get("/rdp/{server_id}")
async def get_rdp_file(server_id: int):
    """Return .rdp file content for download."""
    con = _get_db()
    try:
        row = con.execute("SELECT * FROM bastion_servers WHERE id=?", (server_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Server not found")
        host = row["hostname"]
        port = row["port"] or 3389
        user = row["username"] or ""

        content = "\r\n".join([
            f"full address:s:{host}:{port}",
            "session bpp:i:32",
            "use multimon:i:0",
            "desktopwidth:i:1920",
            "desktopheight:i:1080",
            "smart sizing:i:1",
        ])
        if user:
            content += f"\r\nusername:s:{user}"
        content += "\r\n"

        from fastapi.responses import Response
        return Response(
            content=content,
            media_type="application/x-rdp",
            headers={"Content-Disposition": f'attachment; filename="{row["name"]}.rdp"'},
        )
    finally:
        con.close()


# ── RDP Launch (native mstsc) ─────────────────────────────────────────────────


class RDPLaunchRequest(BaseModel):
    password: str = ""


@router.post("/rdp-launch/{server_id}")
async def rdp_launch(server_id: int, body: RDPLaunchRequest):
    """Launch native mstsc.exe with saved credentials for instant RDP connection."""
    con = _get_db()
    try:
        row = con.execute("SELECT * FROM bastion_servers WHERE id=?", (server_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Server not found")
        if row["protocol"].upper() != "RDP":
            raise HTTPException(400, "Not an RDP server")
        hostname = row["hostname"]
        port = row["port"] or 3389
        username = row["username"] or ""
    finally:
        con.close()

    target = f"{hostname}:{port}" if port != 3389 else hostname
    loop = asyncio.get_event_loop()

    # Save credentials via cmdkey so mstsc connects without prompting
    if username and body.password:
        cmdkey_target = f"TERMSRV/{hostname}"
        await loop.run_in_executor(None, lambda: subprocess.run(
            ["cmdkey", "/generic:" + cmdkey_target, "/user:" + username, "/pass:" + body.password],
            capture_output=True, timeout=5,
        ))
        logger.info("Saved RDP credentials for %s@%s via cmdkey", username, hostname)

    # Launch mstsc
    try:
        await loop.run_in_executor(None, lambda: subprocess.Popen(
            ["mstsc", f"/v:{target}"],
            creationflags=0x00000008,  # DETACHED_PROCESS
        ))
        logger.info("Launched mstsc for %s", target)
        return {"ok": True, "target": target}
    except Exception as e:
        logger.error("Failed to launch mstsc: %s", e)
        raise HTTPException(500, f"Impossible de lancer mstsc: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_server(r) -> ServerResponse:
    keys = r.keys()
    return ServerResponse(
        id=r["id"],
        name=r["name"],
        hostname=r["hostname"],
        port=r["port"],
        username=r["username"] or "",
        protocol=r["protocol"] or "SSH",
        group_name=r["group_name"] or "",
        notes=r["notes"] if "notes" in keys else "",
        ssh_key_path=r["ssh_key_path"] if "ssh_key_path" in keys else "",
        created_at=r["created_at"] or "",
        updated_at=r["updated_at"] or "",
    )

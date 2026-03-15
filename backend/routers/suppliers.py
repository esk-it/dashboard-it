from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from ..database import get_raw_db
from ..schemas.supplier import (
    DomainCreate,
    DomainResponse,
    DomainUpdate,
    SupplierCreate,
    SupplierResponse,
    SupplierUpdate,
)

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])

LOGO_DIR = Path(__file__).parent.parent / "data" / "logos"
LOGO_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


def _row_to_supplier(r) -> dict:
    return {
        "id": r[0],
        "name": r[1],
        "domain": r[2] or "",
        "phone": r[3] or "",
        "email": r[4] or "",
        "contact": r[5] or "",
        "notes": r[6] or "",
        "logo_path": r[7] or "",
        "created_at": r[8] or "",
    }


# ---------------------------------------------------------------------------
# Domain endpoints
# ---------------------------------------------------------------------------

@router.get("/domains", response_model=list[DomainResponse])
async def list_domains(db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT id, name, color_hex, icon_key, sort_order FROM supplier_domains ORDER BY sort_order ASC, name ASC"
    )
    return [
        DomainResponse(id=r[0], name=r[1], color_hex=r[2], icon_key=r[3], sort_order=r[4])
        for r in rows
    ]


@router.post("/domains", response_model=DomainResponse, status_code=201)
async def create_domain(body: DomainCreate, db=Depends(get_raw_db)):
    cursor = await db.execute(
        "INSERT INTO supplier_domains (name, color_hex, icon_key, sort_order) VALUES (?, ?, ?, ?)",
        (body.name, body.color_hex, body.icon_key, body.sort_order),
    )
    await db.commit()
    return DomainResponse(
        id=cursor.lastrowid, name=body.name, color_hex=body.color_hex,
        icon_key=body.icon_key, sort_order=body.sort_order,
    )


@router.put("/domains/{domain_id}", response_model=DomainResponse)
async def update_domain(domain_id: int, body: DomainUpdate, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM supplier_domains WHERE id = ?", (domain_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Domain not found")

    await db.execute(
        "UPDATE supplier_domains SET name=?, color_hex=?, icon_key=?, sort_order=? WHERE id=?",
        (body.name, body.color_hex, body.icon_key, body.sort_order, domain_id),
    )
    await db.commit()
    return DomainResponse(
        id=domain_id, name=body.name, color_hex=body.color_hex,
        icon_key=body.icon_key, sort_order=body.sort_order,
    )


@router.delete("/domains/{domain_id}", status_code=204)
async def delete_domain(domain_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM supplier_domains WHERE id = ?", (domain_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Domain not found")
    await db.execute("DELETE FROM supplier_domains WHERE id = ?", (domain_id,))
    await db.commit()


# ---------------------------------------------------------------------------
# Supplier endpoints
# ---------------------------------------------------------------------------

_SUPPLIER_COLS = """id, name, COALESCE(domain,''), COALESCE(phone,''),
                    COALESCE(email,''), COALESCE(contact,''), COALESCE(notes,''),
                    COALESCE(logo_path,''), COALESCE(created_at,'')"""


@router.get("", response_model=list[SupplierResponse])
async def list_suppliers(
    domain: str = Query(""),
    search: str = Query(""),
    db=Depends(get_raw_db),
):
    query = f"SELECT {_SUPPLIER_COLS} FROM suppliers WHERE 1=1"
    params: list = []

    if domain:
        query += " AND domain = ?"
        params.append(domain)

    if search:
        query += " AND (name LIKE ? OR contact LIKE ? OR notes LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]

    query += " ORDER BY name ASC"

    rows = await db.execute_fetchall(query, params)
    return [SupplierResponse(**_row_to_supplier(r)) for r in rows]


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(supplier_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        f"SELECT {_SUPPLIER_COLS} FROM suppliers WHERE id = ?",
        (supplier_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return SupplierResponse(**_row_to_supplier(rows[0]))


@router.post("", response_model=SupplierResponse, status_code=201)
async def create_supplier(body: SupplierCreate, db=Depends(get_raw_db)):
    now = datetime.now().isoformat(timespec="seconds")
    cursor = await db.execute(
        """INSERT INTO suppliers (name, domain, phone, email, contact, notes, logo_path, created_at)
           VALUES (?, ?, ?, ?, ?, ?, '', ?)""",
        (body.name, body.domain, body.phone, body.email, body.contact, body.notes, now),
    )
    await db.commit()
    supplier_id = cursor.lastrowid
    rows = await db.execute_fetchall(
        f"SELECT {_SUPPLIER_COLS} FROM suppliers WHERE id = ?",
        (supplier_id,),
    )
    return SupplierResponse(**_row_to_supplier(rows[0]))


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(supplier_id: int, body: SupplierUpdate, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM suppliers WHERE id = ?", (supplier_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Supplier not found")

    await db.execute(
        """UPDATE suppliers SET name=?, domain=?, phone=?, email=?, contact=?, notes=?
           WHERE id=?""",
        (body.name, body.domain, body.phone, body.email, body.contact, body.notes, supplier_id),
    )
    await db.commit()
    return await get_supplier(supplier_id, db)


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(supplier_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM suppliers WHERE id = ?", (supplier_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Remove logo file if it exists
    logo_rows = await db.execute_fetchall(
        "SELECT logo_path FROM suppliers WHERE id = ?", (supplier_id,),
    )
    if logo_rows and logo_rows[0][0]:
        logo_file = LOGO_DIR / logo_rows[0][0]
        if logo_file.exists():
            logo_file.unlink()

    await db.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
    await db.commit()


# ---------------------------------------------------------------------------
# Logo endpoints
# ---------------------------------------------------------------------------

@router.post("/{supplier_id}/logo", response_model=SupplierResponse)
async def upload_logo(supplier_id: int, file: UploadFile = File(...), db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT logo_path FROM suppliers WHERE id = ?", (supplier_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Supplier not found")

    ext = Path(file.filename or "upload.png").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")

    content = await file.read()
    hash8 = hashlib.md5(content).hexdigest()[:8]
    filename = f"{supplier_id}_{hash8}{ext}"

    # Remove old logo if present
    old_path = rows[0][0]
    if old_path:
        old_file = LOGO_DIR / old_path
        if old_file.exists():
            old_file.unlink()

    (LOGO_DIR / filename).write_bytes(content)

    await db.execute(
        "UPDATE suppliers SET logo_path = ? WHERE id = ?",
        (filename, supplier_id),
    )
    await db.commit()
    return await get_supplier(supplier_id, db)


@router.get("/{supplier_id}/logo")
async def serve_logo(supplier_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT logo_path FROM suppliers WHERE id = ?", (supplier_id,),
    )
    if not rows or not rows[0][0]:
        raise HTTPException(status_code=404, detail="Logo not found")

    logo_path = LOGO_DIR / rows[0][0]
    if not logo_path.exists():
        raise HTTPException(status_code=404, detail="Logo file not found")

    ext = logo_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return Response(
        content=logo_path.read_bytes(),
        media_type=media_type,
        headers={"Content-Disposition": "inline"},
    )

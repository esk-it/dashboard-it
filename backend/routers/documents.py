from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from ..database import get_raw_db

VAULT_ROOT = Path(__file__).parent.parent / "data" / "documents"
VAULT_ROOT.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
               ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp",
               ".txt", ".csv", ".zip", ".rar", ".7z"}

MIME_MAP = {
    ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".gif": "image/gif", ".bmp": "image/bmp",
    ".svg": "image/svg+xml", ".webp": "image/webp",
    ".doc": "application/msword", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".txt": "text/plain", ".csv": "text/csv",
}
from ..schemas.document import (
    DocumentCreate,
    DocumentDetailResponse,
    DocumentLinkCreate,
    DocumentLinkResponse,
    DocumentResponse,
    DocumentUpdate,
    TagResponse,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _row_to_document(r) -> dict:
    return {
        "id": r[0],
        "title": r[1],
        "doc_type": r[2] or "",
        "supplier_id": r[3],
        "supplier_name": r[4] or "",
        "doc_date": r[5],
        "reference": r[6] or "",
        "file_path": r[7] or "",
        "file_hash": r[8] or "",
        "notes": r[9] or "",
        "created_at": r[10] or "",
    }


@router.get("/types")
async def list_doc_types(db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT DISTINCT doc_type FROM documents WHERE doc_type IS NOT NULL AND doc_type != '' ORDER BY doc_type ASC"
    )
    return [r[0] for r in rows]


@router.get("/tags", response_model=list[TagResponse])
async def list_tags(db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT id, name, COALESCE(created_at,'') FROM tags ORDER BY name ASC"
    )
    return [TagResponse(id=r[0], name=r[1], created_at=r[2]) for r in rows]


# ── Document Links (static prefix must come BEFORE /{doc_id}) ──


@router.delete("/links/{link_id}", status_code=204)
async def delete_document_link(link_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        "SELECT id FROM document_links WHERE id = ?", (link_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Link not found")
    await db.execute("DELETE FROM document_links WHERE id = ?", (link_id,))
    await db.commit()


# ── File upload helpers ─────────────────────────────────────────

def _detect_doc_type(filename: str) -> str:
    """Auto-detect document type from filename patterns."""
    name = filename.upper()
    if re.search(r"DEVIS|QUOTE|QUOTATION|PROFORMA", name):
        return "DEVIS"
    if re.search(r"FACTURE|INVOICE|FACT[_\-]", name):
        return "FACTURE"
    if re.search(r"CONTRAT|CONTRACT|AGREEMENT", name):
        return "CONTRAT"
    if re.search(r"BON|BPA|BC[_\-]|ORDER", name):
        return "BON"
    if re.search(r"RAPPORT|REPORT|CR[_\-]|COMPTE[_\-]?RENDU", name):
        return "RAPPORT"
    return ""


def _detect_date(filename: str) -> str:
    """Try to extract a date from filename (multiple formats)."""
    # 2024-01-15 or 2024_01_15
    m = re.search(r"(20\d{2})[\-_](0[1-9]|1[0-2])[\-_](0[1-9]|[12]\d|3[01])", filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    # 15-01-2024 or 15_01_2024
    m = re.search(r"(0[1-9]|[12]\d|3[01])[\-_](0[1-9]|1[0-2])[\-_](20\d{2})", filename)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # 20240115
    m = re.search(r"(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])", filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def _sanitize_filename(name: str) -> str:
    """Remove dangerous characters from a filename."""
    name = Path(name).name  # strip any directory components
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    return name.strip() or "document"


async def _store_file(file: UploadFile, doc_type: str) -> tuple[str, str]:
    """Copy uploaded file into vault, return (relative_path, sha256)."""
    content = await file.read()
    sha = hashlib.sha256(content).hexdigest()

    ext = Path(file.filename or "file").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Extension {ext} non autorisée")

    year = str(datetime.now().year)
    dtype_folder = (doc_type or "AUTRE").upper()
    safe_name = _sanitize_filename(file.filename or "document" + ext)

    dest_dir = VAULT_ROOT / year / dtype_folder
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / safe_name
    # Handle duplicates: add hash prefix
    if dest.exists():
        stem = dest.stem
        dest = dest_dir / f"{stem}_{sha[:8]}{ext}"

    dest.write_bytes(content)
    # Store relative path from VAULT_ROOT
    rel_path = str(dest.relative_to(VAULT_ROOT)).replace("\\", "/")
    return rel_path, sha


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(""),
    doc_type: str = Form(""),
    supplier: str = Form(""),
    doc_date: str = Form(""),
    reference: str = Form(""),
    notes: str = Form(""),
    tags: str = Form(""),
    db=Depends(get_raw_db),
):
    """Upload a single file and create a document record."""
    filename = file.filename or "document"

    # Auto-detect metadata from filename if not provided
    if not doc_type:
        doc_type = _detect_doc_type(filename)
    if not doc_date:
        doc_date = _detect_date(filename)
    if not title:
        title = Path(filename).stem.replace("_", " ").replace("-", " ").strip()

    rel_path, sha = await _store_file(file, doc_type)

    # Check for duplicate by hash
    existing = await db.execute_fetchall(
        "SELECT id FROM documents WHERE file_hash = ?", (sha,)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Ce fichier existe déjà (doublon SHA256)")

    # Resolve supplier_id from name if provided
    supplier_id = None
    if supplier:
        rows = await db.execute_fetchall(
            "SELECT id FROM suppliers WHERE name LIKE ?", (f"%{supplier}%",)
        )
        if rows:
            supplier_id = rows[0][0]

    now = datetime.now().isoformat(timespec="seconds")
    cursor = await db.execute(
        """INSERT INTO documents (title, doc_type, supplier_id, doc_date, reference, file_path, file_hash, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, doc_type, supplier_id, doc_date, reference, rel_path, sha, notes, now),
    )
    await db.commit()
    return await _fetch_document_response(db, cursor.lastrowid)


@router.post("/upload-folder", status_code=201)
async def upload_folder(
    files: List[UploadFile] = File(...),
    doc_type: str = Form(""),
    supplier: str = Form(""),
    tags: str = Form(""),
    db=Depends(get_raw_db),
):
    """Upload multiple files at once (folder import)."""
    # Resolve supplier_id from name if provided
    supplier_id = None
    if supplier:
        rows = await db.execute_fetchall(
            "SELECT id FROM suppliers WHERE name LIKE ?", (f"%{supplier}%",)
        )
        if rows:
            supplier_id = rows[0][0]

    created = []
    skipped = 0
    now = datetime.now().isoformat(timespec="seconds")

    for file in files:
        filename = file.filename or "document"
        file_doc_type = doc_type or _detect_doc_type(filename)
        file_date = _detect_date(filename)
        file_title = Path(filename).stem.replace("_", " ").replace("-", " ").strip()

        try:
            rel_path, sha = await _store_file(file, file_doc_type)
        except HTTPException:
            skipped += 1
            continue

        # Skip duplicates silently in batch mode
        existing = await db.execute_fetchall(
            "SELECT id FROM documents WHERE file_hash = ?", (sha,)
        )
        if existing:
            skipped += 1
            continue

        cursor = await db.execute(
            """INSERT INTO documents (title, doc_type, supplier_id, doc_date, reference, file_path, file_hash, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (file_title, file_doc_type, supplier_id, file_date, "", rel_path, sha, "", now),
        )
        created.append(cursor.lastrowid)

    await db.commit()
    return {"created": len(created), "skipped": skipped, "ids": created}


# ── Preview (static prefix, must come BEFORE /{doc_id}) ────────


@router.get("/preview/{doc_id}")
async def preview_document_alt(doc_id: int, db=Depends(get_raw_db)):
    """Alternative preview route (kept for compat)."""
    return await _serve_preview(db, doc_id)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    search: str = Query(""),
    doc_type: str = Query(""),
    supplier_id: int | None = Query(None),
    db=Depends(get_raw_db),
):
    query = """SELECT d.id, d.title, COALESCE(d.doc_type,''), d.supplier_id,
                      COALESCE(s.name,'') as supplier_name,
                      d.doc_date, COALESCE(d.reference,''),
                      COALESCE(d.file_path,''), COALESCE(d.file_hash,''),
                      COALESCE(d.notes,''), COALESCE(d.created_at,'')
               FROM documents d
               LEFT JOIN suppliers s ON d.supplier_id = s.id
               WHERE 1=1"""
    params: list = []

    if search:
        query += " AND (d.title LIKE ? OR d.reference LIKE ? OR d.notes LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]

    if doc_type:
        query += " AND d.doc_type = ?"
        params.append(doc_type)

    if supplier_id is not None:
        query += " AND d.supplier_id = ?"
        params.append(supplier_id)

    query += " ORDER BY d.created_at DESC"

    rows = await db.execute_fetchall(query, params)
    return [DocumentResponse(**_row_to_document(r)) for r in rows]


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(doc_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        """SELECT d.id, d.title, COALESCE(d.doc_type,''), d.supplier_id,
                  COALESCE(s.name,'') as supplier_name,
                  d.doc_date, COALESCE(d.reference,''),
                  COALESCE(d.file_path,''), COALESCE(d.file_hash,''),
                  COALESCE(d.notes,''), COALESCE(d.created_at,'')
           FROM documents d
           LEFT JOIN suppliers s ON d.supplier_id = s.id
           WHERE d.id = ?""",
        (doc_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = _row_to_document(rows[0])

    # Fetch tags
    tag_rows = await db.execute_fetchall(
        """SELECT t.id, t.name, COALESCE(t.created_at,'')
           FROM tags t
           JOIN document_tags dt ON dt.tag_id = t.id
           WHERE dt.document_id = ?
           ORDER BY t.name ASC""",
        (doc_id,),
    )
    tags = [TagResponse(id=r[0], name=r[1], created_at=r[2]) for r in tag_rows]

    # Fetch links
    link_rows = await db.execute_fetchall(
        """SELECT id, source_id, target_id, COALESCE(link_type,''), COALESCE(created_at,'')
           FROM document_links
           WHERE source_id = ? OR target_id = ?""",
        (doc_id, doc_id),
    )
    links = [
        DocumentLinkResponse(
            id=r[0], source_id=r[1], target_id=r[2], link_type=r[3], created_at=r[4]
        )
        for r in link_rows
    ]

    return DocumentDetailResponse(**doc, tags=tags, links=links)


@router.get("/{doc_id}/preview")
async def preview_document(doc_id: int, db=Depends(get_raw_db)):
    """Serve the document file from the vault for inline preview."""
    return await _serve_preview(db, doc_id)


@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(body: DocumentCreate, db=Depends(get_raw_db)):
    now = datetime.now().isoformat(timespec="seconds")
    cursor = await db.execute(
        """INSERT INTO documents (title, doc_type, supplier_id, doc_date, reference, file_path, file_hash, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            body.title,
            body.doc_type,
            body.supplier_id,
            body.doc_date,
            body.reference,
            body.file_path,
            body.file_hash,
            body.notes,
            now,
        ),
    )
    await db.commit()
    doc_id = cursor.lastrowid

    # Insert tags
    for tag_id in body.tag_ids:
        await db.execute(
            "INSERT OR IGNORE INTO document_tags (document_id, tag_id) VALUES (?, ?)",
            (doc_id, tag_id),
        )
    if body.tag_ids:
        await db.commit()

    return await _fetch_document_response(db, doc_id)


@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(doc_id: int, body: DocumentUpdate, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM documents WHERE id = ?", (doc_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.execute(
        """UPDATE documents SET title=?, doc_type=?, supplier_id=?, doc_date=?, reference=?, file_path=?, file_hash=?, notes=?
           WHERE id=?""",
        (
            body.title,
            body.doc_type,
            body.supplier_id,
            body.doc_date,
            body.reference,
            body.file_path,
            body.file_hash,
            body.notes,
            doc_id,
        ),
    )

    # Update tags: delete old, insert new
    await db.execute("DELETE FROM document_tags WHERE document_id = ?", (doc_id,))
    for tag_id in body.tag_ids:
        await db.execute(
            "INSERT OR IGNORE INTO document_tags (document_id, tag_id) VALUES (?, ?)",
            (doc_id, tag_id),
        )
    await db.commit()

    return await _fetch_document_response(db, doc_id)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall("SELECT id FROM documents WHERE id = ?", (doc_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.execute("DELETE FROM document_tags WHERE document_id = ?", (doc_id,))
    await db.execute(
        "DELETE FROM document_links WHERE source_id = ? OR target_id = ?",
        (doc_id, doc_id),
    )
    await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    await db.commit()


# ── Document Links ──────────────────────────────────────────────


@router.get("/{doc_id}/links", response_model=list[DocumentLinkResponse])
async def get_document_links(doc_id: int, db=Depends(get_raw_db)):
    rows = await db.execute_fetchall(
        """SELECT id, source_id, target_id, COALESCE(link_type,''), COALESCE(created_at,'')
           FROM document_links
           WHERE source_id = ? OR target_id = ?""",
        (doc_id, doc_id),
    )
    return [
        DocumentLinkResponse(
            id=r[0], source_id=r[1], target_id=r[2], link_type=r[3], created_at=r[4]
        )
        for r in rows
    ]


@router.post("/{doc_id}/links", response_model=DocumentLinkResponse, status_code=201)
async def create_document_link(
    doc_id: int, body: DocumentLinkCreate, db=Depends(get_raw_db)
):
    # Verify both documents exist
    for did in (doc_id, body.target_id):
        rows = await db.execute_fetchall(
            "SELECT id FROM documents WHERE id = ?", (did,)
        )
        if not rows:
            raise HTTPException(
                status_code=404, detail=f"Document {did} not found"
            )

    now = datetime.now().isoformat(timespec="seconds")
    cursor = await db.execute(
        """INSERT INTO document_links (source_id, target_id, link_type, created_at)
           VALUES (?, ?, ?, ?)""",
        (doc_id, body.target_id, body.link_type, now),
    )
    await db.commit()
    return DocumentLinkResponse(
        id=cursor.lastrowid,
        source_id=doc_id,
        target_id=body.target_id,
        link_type=body.link_type,
        created_at=now,
    )


async def _serve_preview(db, doc_id: int):
    """Serve a document file from the vault."""
    rows = await db.execute_fetchall(
        "SELECT file_path FROM documents WHERE id = ?", (doc_id,)
    )
    if not rows or not rows[0][0]:
        raise HTTPException(status_code=404, detail="Document or file not found")

    rel_path = rows[0][0]
    full_path = VAULT_ROOT / rel_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found on disk: {rel_path}")

    ext = full_path.suffix.lower()
    media_type = MIME_MAP.get(ext, "application/octet-stream")
    content = full_path.read_bytes()
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{full_path.name}"',
        },
    )


async def _fetch_document_response(db, doc_id: int) -> DocumentResponse:
    rows = await db.execute_fetchall(
        """SELECT d.id, d.title, COALESCE(d.doc_type,''), d.supplier_id,
                  COALESCE(s.name,'') as supplier_name,
                  d.doc_date, COALESCE(d.reference,''),
                  COALESCE(d.file_path,''), COALESCE(d.file_hash,''),
                  COALESCE(d.notes,''), COALESCE(d.created_at,'')
           FROM documents d
           LEFT JOIN suppliers s ON d.supplier_id = s.id
           WHERE d.id = ?""",
        (doc_id,),
    )
    return DocumentResponse(**_row_to_document(rows[0]))

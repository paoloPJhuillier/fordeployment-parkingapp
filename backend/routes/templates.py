import os
import io
import zipfile
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, FileResponse, StreamingResponse

from auth.security import require_admin

router = APIRouter()

DOCS_OUTPUT_DIR = Path("/app/docs/output")


@router.get("/templates/users")
async def download_users_template(current_user: dict = Depends(require_admin)):
    csv_content = "email,first_name,last_name,company,role,job_family,main_building,zone\njuan.delacruz@cebuana.com,Juan,Dela Cruz,Cebuana Lhuillier,user,Department Head,CL Tower Makati,Metro Manila Zone\nmaria.santos@cebuana.com,Maria,Santos,Cebuana Lhuillier,attendant,,,\n"
    return Response(content=csv_content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=users_template.csv"})


@router.get("/templates/buildings")
async def download_buildings_template(current_user: dict = Depends(require_admin)):
    csv_content = 'building_name,floor_label,slot_labels\nCL Tower Makati,1F,"A1,A2,A3,A4,A5"\nCL Tower Makati,2F,"B1,B2,B3,B4,B5"\nMain Office,GF,"P1,P2,P3,P4"\n'
    return Response(content=csv_content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=buildings_template.csv"})


@router.get("/templates/zones")
async def download_zones_template(current_user: dict = Depends(require_admin)):
    csv_content = 'zone_name,building_names\nMetro Manila Zone,"CL Tower Makati,Main Office"\nVisayas Zone,"Cebu Branch,Iloilo Branch"\n'
    return Response(content=csv_content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=zones_template.csv"})



@router.get("/docs/list")
async def list_documentation(current_user: dict = Depends(require_admin)):
    """List all available documentation files."""
    if not DOCS_OUTPUT_DIR.exists():
        return {"files": []}
    files = []
    for f in sorted(DOCS_OUTPUT_DIR.iterdir()):
        if f.suffix in ('.docx', '.pdf'):
            files.append({
                "name": f.name,
                "format": f.suffix[1:],
                "size_kb": round(f.stat().st_size / 1024),
            })
    return {"files": files}


@router.get("/docs/download/{filename}")
async def download_documentation(filename: str, current_user: dict = Depends(require_admin)):
    """Download a documentation file."""
    import re
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    if not safe_name or '..' in safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    filepath = DOCS_OUTPUT_DIR / safe_name
    if not filepath.exists() or not filepath.resolve().is_relative_to(DOCS_OUTPUT_DIR.resolve()):
        raise HTTPException(status_code=404, detail="File not found")
    media_types = {
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.pdf': 'application/pdf',
    }
    media_type = media_types.get(filepath.suffix, 'application/octet-stream')
    return FileResponse(str(filepath), media_type=media_type, filename=safe_name)


@router.get("/docs/download-zip")
async def download_docs_zip(format: str = "all", current_user: dict = Depends(require_admin)):
    """Download documentation as a zip. format: pdf, docx, or all."""
    if not DOCS_OUTPUT_DIR.exists():
        raise HTTPException(status_code=404, detail="No documentation files found")

    ext_filter = None
    if format == "pdf":
        ext_filter = ".pdf"
        zip_name = "Documentation_PDF.zip"
    elif format == "docx":
        ext_filter = ".docx"
        zip_name = "Documentation_Word.zip"
    else:
        zip_name = "Documentation_All.zip"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(DOCS_OUTPUT_DIR.iterdir()):
            if f.suffix not in ('.docx', '.pdf'):
                continue
            if ext_filter and f.suffix != ext_filter:
                continue
            zf.write(f, f.name)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_name}"'}
    )

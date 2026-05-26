import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from controllers.file_controller import FileController
from controllers.auth_controller import get_current_user
from services.file_service import FileService
from utils.logger import write_log

router = APIRouter(prefix="/files", tags=["Files"])

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    result = await FileController.upload_file(file, current_user)
    return result

@router.get("/view/{filename}")
async def view_file(
    filename: str,
    current_user = Depends(get_current_user)
):
    content, file_info = FileController.view_file(filename, current_user)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {
        "content": content,
        "filename": filename,
        "file_info": file_info
    }

@router.post("/edit/{filename}")
async def edit_file(
    filename: str,
    content: str = Form(...),
    current_user = Depends(get_current_user)
):
    success, message = FileController.edit_file(filename, content, current_user)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}

@router.delete("/{filename}")
async def delete_file(
    filename: str,
    permanent: bool = False,
    current_user = Depends(get_current_user)
):
    success = FileController.delete_file(filename, current_user, permanent)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {"message": "File deleted" if not permanent else "File permanently deleted"}

@router.post("/{filename}/restore")
async def restore_file(
    filename: str,
    current_user = Depends(get_current_user)
):
    success = FileController.restore_file(filename, current_user)
    if not success:
        raise HTTPException(status_code=404, detail="File not found in trash")
    
    return {"message": "File restored"}

@router.put("/rename/{old_filename}")
async def rename_file(
    old_filename: str,
    new_filename: str,
    current_user = Depends(get_current_user)
):
    user_dir = FileService.get_user_dir(current_user['username'])
    old_path = os.path.join(user_dir, old_filename)
    new_path = os.path.join(user_dir, new_filename)
    
    if not os.path.exists(old_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    if os.path.exists(new_path):
        raise HTTPException(status_code=409, detail="File already exists")
    
    os.rename(old_path, new_path)
    
    write_log(
        event_type="file_renamed",
        uid=current_user['uid'],
        uid_type="name",
        params={"old_filename": old_filename, "new_filename": new_filename},
        role=current_user['role']
    )
    
    return {"message": "File renamed successfully", "old": old_filename, "new": new_filename}

@router.get("/list")
async def list_files(current_user = Depends(get_current_user)):
    files = FileService.list_user_files(current_user['username'])
    return files

@router.get("/trash")
async def list_trash(current_user = Depends(get_current_user)):
    files = FileService.list_trash_files(current_user['username'])
    return files

@router.get("/info/{filename}")
async def get_file_info(
    filename: str,
    current_user = Depends(get_current_user)
):
    info = FileController.get_file_info(filename, current_user)
    if not info:
        raise HTTPException(status_code=404, detail="File not found")
    return info

@router.get("/download/{filename}")
async def download_file(
    filename: str,
    token: str = None,
    current_user = Depends(get_current_user)
):
    user_dir = FileService.get_user_dir(current_user['username'])
    filepath = os.path.join(user_dir, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    write_log(
        event_type="file_downloaded",
        uid=current_user['uid'],
        uid_type="name",
        params={"filename": filename, "size": os.path.getsize(filepath)},
        role=current_user['role']
    )
    
    return FileResponse(filepath, filename=filename)
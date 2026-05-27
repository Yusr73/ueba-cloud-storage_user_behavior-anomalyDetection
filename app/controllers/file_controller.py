import os
import hashlib
from datetime import datetime
from services.file_service import FileService
from models.file_model import FileModel
from utils.logger import write_log

class FileController:
    @staticmethod
    async def upload_file(file, current_user):
        content = await file.read()
        
        # Vérifier si le fichier existe déjà
        user_dir = FileService.get_user_dir(current_user['username'])
        file_exists = os.path.exists(os.path.join(user_dir, file.filename))
        
        filepath, size, file_hash = FileService.save_file(content, current_user['username'], file.filename)
        
        FileModel.track_file(file.filename, filepath, current_user['uid'], size, file_hash)
        
        if file_exists:
            # Upload du même fichier = mise à jour des métadonnées (taille, hash, version)
            write_log(
                event_type="file_updated",
                uid=current_user['uid'],
                uid_type="uid",
                params={"filename": file.filename, "size": size, "hash": file_hash, "action": "overwrite"},
                role=current_user['role'],
                is_local_ip=True,
                location={"city": "unknown"}
            )
        else:
            # Nouveau fichier
            write_log(
                event_type="file_created",
                uid=current_user['uid'],
                uid_type="uid",
                params={"filename": file.filename, "size": size, "hash": file_hash},
                role=current_user['role'],
                is_local_ip=True,
                location={"city": "unknown"}
            )
        
        return {"filename": file.filename, "size": size}
    
    @staticmethod
    def view_file(filename: str, current_user):
        content, file_type = FileService.read_file_content(current_user['username'], filename)
        
        if content is None:
            return None, None
        
        file_info = FileService.get_file_info(current_user['username'], filename)
        
        write_log(
            event_type="file_accessed",
            uid=current_user['uid'],
            uid_type="uid",
            params={"filename": filename, "action": "view", "file_type": file_type},
            role=current_user['role'],
            is_local_ip=True,
            location={"city": "unknown"}
        )
        
        return content, file_info
    
    @staticmethod
    def edit_file(filename: str, content: str, current_user):
        success, message = FileService.update_file_content(current_user['username'], filename, content)
        
        if success:
            # Modification du contenu du fichier
            write_log(
                event_type="file_written",
                uid=current_user['uid'],
                uid_type="uid",
                params={"filename": filename, "action": "edit"},
                role=current_user['role'],
                is_local_ip=True,
                location={"city": "unknown"}
            )
        
        return success, message
    
    @staticmethod
    def delete_file(filename: str, current_user, permanent: bool = False):
        if permanent:
            success = FileService.permanent_delete(current_user['username'], filename)
            log_type = "deleted_from_trashbin"
        else:
            new_path = FileService.move_to_trash(current_user['username'], filename)
            success = new_path is not None
            log_type = "file_deleted"

        if success:
            write_log(
                event_type=log_type,
                uid=current_user['uid'],
                uid_type="uid",
                params={"filename": filename},
                role=current_user['role'],
                is_local_ip=True,
                location={"city": "unknown"}
            )
            
            FileModel.mark_deleted(filename, current_user['uid'], permanent)

        return success
    
    @staticmethod
    def restore_file(filename: str, current_user):
        success = FileService.restore_from_trash(current_user['username'], filename)
        
        if success:
            # Restaurer = mise à jour des métadonnées (deleted_at, in_trash)
            write_log(
                event_type="file_updated",
                uid=current_user['uid'],
                uid_type="uid",
                params={"filename": filename, "action": "restored_from_trash"},
                role=current_user['role'],
                is_local_ip=True,
                location={"city": "unknown"}
            )
        
        return success
    
    @staticmethod
    def rename_file(old_filename: str, new_filename: str, current_user):
        user_dir = FileService.get_user_dir(current_user['username'])
        old_path = os.path.join(user_dir, old_filename)
        new_path = os.path.join(user_dir, new_filename)
        
        if not os.path.exists(old_path):
            return False, "File not found"
        
        if os.path.exists(new_path):
            return False, "File with this name already exists"
        
        os.rename(old_path, new_path)
        
        write_log(
            event_type="file_renamed",
            uid=current_user['uid'],
            uid_type="uid",
            params={"old_filename": old_filename, "new_filename": new_filename},
            role=current_user['role'],
            is_local_ip=True,
            location={"city": "unknown"}
        )
        
        return True, "File renamed successfully"
    
    @staticmethod
    def share_file(filename: str, current_user):
        user_dir = FileService.get_user_dir(current_user['username'])
        file_path = os.path.join(user_dir, filename)
        
        if not os.path.exists(file_path):
            return False, "File not found"
        
        share_token = hashlib.md5(
            f"{current_user['uid']}{filename}{datetime.now().timestamp()}".encode()
        ).hexdigest()[:16]
        
        write_log(
            event_type="shared_user",
            uid=current_user['uid'],
            uid_type="uid",
            params={"filename": filename, "share_token": share_token},
            role=current_user['role'],
            is_local_ip=True,
            location={"city": "unknown"}
        )
        
        return True, {"share_link": f"/shared/{share_token}", "share_token": share_token}
    
    @staticmethod
    def get_file_info(filename: str, current_user):
        return FileService.get_file_info(current_user['username'], filename)
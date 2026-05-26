from services.file_service import FileService
from models.file_model import FileModel
from utils.logger import write_log
import os

class FileController:
    @staticmethod
    async def upload_file(file, current_user):
        content = await file.read()
        filepath, size, file_hash = FileService.save_file(content, current_user['username'], file.filename)
        
        # Track in database
        FileModel.track_file(file.filename, filepath, current_user['uid'], size, file_hash)
        
        # Log the event
        write_log(
            event_type="file_created",
            uid=current_user['uid'],
            uid_type="name",
            params={"filename": file.filename, "size": size, "hash": file_hash},
            role=current_user['role']
        )
        
        return {"filename": file.filename, "size": size}
    
    @staticmethod
    def view_file(filename: str, current_user):
        content, file_type = FileService.read_file_content(current_user['username'], filename)
        
        if content is None:
            return None, None
        
        # Get file info
        file_info = FileService.get_file_info(current_user['username'], filename)
        
        # Log file access
        write_log(
            event_type="file_accessed",
            uid=current_user['uid'],
            uid_type="name",
            params={"filename": filename, "action": "view", "file_type": file_type},
            role=current_user['role']
        )
        
        return content, file_info
    
    @staticmethod
    def edit_file(filename: str, content: str, current_user):
        success, message = FileService.update_file_content(current_user['username'], filename, content)
        
        if success:
            # Log file edit/update
            write_log(
                event_type="file_updated",
                uid=current_user['uid'],
                uid_type="name",
                params={"filename": filename, "action": "edit"},
                role=current_user['role']
            )
            
            write_log(
                event_type="file_written",
                uid=current_user['uid'],
                uid_type="name",
                params={"filename": filename, "action": "save"},
                role=current_user['role']
            )
        
        return success, message
    
    @staticmethod
    def delete_file(filename: str, current_user, permanent: bool = False):
        if permanent:
            success = FileService.permanent_delete(current_user['username'], filename)
            log_type = "file_permanently_deleted"
        else:
            new_path = FileService.move_to_trash(current_user['username'], filename)
            success = new_path is not None
            log_type = "file_deleted"
        
        if success:
            write_log(
                event_type=log_type,
                uid=current_user['uid'],
                uid_type="name",
                params={"filename": filename, "permanent": permanent},
                role=current_user['role']
            )
            
            if not permanent:
                write_log(
                    event_type="moved_to_trash",
                    uid=current_user['uid'],
                    uid_type="name",
                    params={"filename": filename},
                    role=current_user['role']
                )
            
            FileModel.mark_deleted(filename, current_user['uid'], permanent)
        
        return success
    
    @staticmethod
    def restore_file(filename: str, current_user):
        success = FileService.restore_from_trash(current_user['username'], filename)
        
        if success:
            write_log(
                event_type="restored_from_trash",
                uid=current_user['uid'],
                uid_type="name",
                params={"filename": filename},
                role=current_user['role']
            )
        
        return success
    
    @staticmethod
    def rename_file(old_filename: str, new_filename: str, current_user):
        user_dir = FileService.get_user_dir(current_user['username'])
        old_path = os.path.join(user_dir, old_filename)
        new_path = os.path.join(user_dir, new_filename)
        
        if os.path.exists(old_path) and not os.path.exists(new_path):
            os.rename(old_path, new_path)
            
            write_log(
                event_type="file_renamed",
                uid=current_user['uid'],
                uid_type="name",
                params={"old_filename": old_filename, "new_filename": new_filename},
                role=current_user['role']
            )
            return True, "File renamed"
        elif os.path.exists(new_path):
            return False, "File with this name already exists"
        return False, "File not found"
    
    @staticmethod
    def get_file_info(filename: str, current_user):
        return FileService.get_file_info(current_user['username'], filename)
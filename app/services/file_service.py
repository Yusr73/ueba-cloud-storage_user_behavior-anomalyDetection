import os
import shutil
import hashlib
import mimetypes
from pathlib import Path
from config import Config

class FileService:
    @staticmethod
    def get_user_dir(username: str):
        user_dir = os.path.join(Config.UPLOAD_BASE_DIR, username)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    @staticmethod
    def get_trash_dir(username: str):
        trash_dir = os.path.join(Config.TRASH_DIR, username)
        os.makedirs(trash_dir, exist_ok=True)
        return trash_dir
    
    @staticmethod
    def save_file(file_content: bytes, username: str, filename: str):
        user_dir = FileService.get_user_dir(username)
        filepath = os.path.join(user_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(file_content)
        
        file_hash = hashlib.md5(file_content).hexdigest()
        return filepath, len(file_content), file_hash
    
    @staticmethod
    def read_file_content(username: str, filename: str):
        user_dir = FileService.get_user_dir(username)
        filepath = os.path.join(user_dir, filename)
        
        if not os.path.exists(filepath):
            return None, None
        
        # Get file extension
        ext = os.path.splitext(filename)[1].lower()
        
        # Text-based files that can be displayed/edited
        text_extensions = {
            '.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', 
            '.csv', '.log', '.sh', '.bat', '.yml', '.yaml', '.conf', '.cfg',
            '.ini', '.properties', '.java', '.c', '.cpp', '.h', '.go', '.rs',
            '.php', '.rb', '.pl', '.lua', '.sql', '.vue', '.jsx', '.tsx', '.ts'
        }
        
        # Image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'}
        
        # PDF files
        pdf_extensions = {'.pdf'}
        
        if ext in text_extensions:
            # Read as text
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content, 'text'
            except UnicodeDecodeError:
                # Try different encoding
                try:
                    with open(filepath, 'r', encoding='latin-1') as f:
                        content = f.read()
                    return content, 'text'
                except:
                    return None, None
        elif ext in image_extensions:
            # Return base64 for images
            import base64
            with open(filepath, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
                mime_type = mimetypes.guess_type(filename)[0] or 'image/png'
                return f"data:{mime_type};base64,{image_data}", 'image'
        elif ext in pdf_extensions:
            # Return PDF as binary
            with open(filepath, 'rb') as f:
                import base64
                pdf_data = base64.b64encode(f.read()).decode('utf-8')
                return pdf_data, 'pdf'
        else:
            # Binary file
            with open(filepath, 'rb') as f:
                import base64
                binary_data = base64.b64encode(f.read()).decode('utf-8')
                return binary_data, 'binary'
    
    @staticmethod
    def update_file_content(username: str, filename: str, content: str):
        user_dir = FileService.get_user_dir(username)
        filepath = os.path.join(user_dir, filename)
        
        # Only allow editing text files
        ext = os.path.splitext(filename)[1].lower()
        text_extensions = {
            '.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', 
            '.csv', '.log', '.sh', '.bat', '.yml', '.yaml', '.conf', '.cfg',
            '.ini', '.properties'
        }
        
        if ext not in text_extensions:
            return False, "Cannot edit binary files"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "Saved"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def move_to_trash(username: str, filename: str):
        user_dir = FileService.get_user_dir(username)
        trash_dir = FileService.get_trash_dir(username)
        
        src = os.path.join(user_dir, filename)
        dst = os.path.join(trash_dir, filename)
        
        if os.path.exists(src):
            # Handle duplicate filenames in trash
            if os.path.exists(dst):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(os.path.join(trash_dir, f"{base}_{counter}{ext}")):
                    counter += 1
                dst = os.path.join(trash_dir, f"{base}_{counter}{ext}")
            
            shutil.move(src, dst)
            return dst
        return None
    
    @staticmethod
    def restore_from_trash(username: str, filename: str):
        trash_dir = FileService.get_trash_dir(username)
        user_dir = FileService.get_user_dir(username)
        
        src = os.path.join(trash_dir, filename)
        dst = os.path.join(user_dir, filename)
        
        if os.path.exists(src):
            shutil.move(src, dst)
            return True
        return False
    
    @staticmethod
    def permanent_delete(username: str, filename: str):
        trash_dir = FileService.get_trash_dir(username)
        filepath = os.path.join(trash_dir, filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    
    @staticmethod
    def list_user_files(username: str):
        user_dir = FileService.get_user_dir(username)
        files = []
        
        if os.path.exists(user_dir):
            for filename in os.listdir(user_dir):
                filepath = os.path.join(user_dir, filename)
                if os.path.isfile(filepath):
                    files.append({
                        "name": filename,
                        "size": os.path.getsize(filepath),
                        "modified": os.path.getmtime(filepath),
                        "extension": os.path.splitext(filename)[1].lower()
                    })
        return sorted(files, key=lambda x: x['modified'], reverse=True)
    
    @staticmethod
    def list_trash_files(username: str):
        trash_dir = FileService.get_trash_dir(username)
        files = []
        
        if os.path.exists(trash_dir):
            for filename in os.listdir(trash_dir):
                filepath = os.path.join(trash_dir, filename)
                if os.path.isfile(filepath):
                    files.append({
                        "name": filename,
                        "size": os.path.getsize(filepath),
                        "deleted_at": os.path.getmtime(filepath)
                    })
        return sorted(files, key=lambda x: x['deleted_at'], reverse=True)
    
    @staticmethod
    def get_file_info(username: str, filename: str):
        user_dir = FileService.get_user_dir(username)
        filepath = os.path.join(user_dir, filename)
        
        if not os.path.exists(filepath):
            return None
        
        ext = os.path.splitext(filename)[1].lower()
        text_extensions = {'.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', '.csv', '.log'}
        
        return {
            "name": filename,
            "size": os.path.getsize(filepath),
            "modified": os.path.getmtime(filepath),
            "extension": ext,
            "is_editable": ext in text_extensions,
            "is_image": ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'},
            "is_pdf": ext == '.pdf'
        }
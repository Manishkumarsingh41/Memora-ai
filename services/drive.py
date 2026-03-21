from config import get_settings
from logging_config import get_logger
import io
import os

settings = get_settings()
logger = get_logger("drive")
SCOPES = ["https://www.googleapis.com/auth/drive"]

FOLDER_MAP = {"pdf": "documents", "image": "images", "video": "videos"}

def _get_service():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            settings.google_credentials_path, scopes=SCOPES
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

def _find_or_create_folder(service, parent_id: str, folder_name: str) -> str:
    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
        results = service.files().list(q=query, spaces="drive", fields="files(id, name)", pageSize=1).execute()
        
        if results.get("files"):
            return results["files"][0]["id"]
        
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = service.files().create(body=file_metadata, fields="id").execute()
        return folder.get("id")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

def _get_or_create_user_folder(service, user_id: str) -> str:
    try:
        root_id = _find_or_create_folder(service, "root", settings.google_drive_root_folder)
        user_folder_id = _find_or_create_folder(service, root_id, user_id)
        return user_folder_id
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

def upload_file(user_id: str, local_path: str, file_name: str, file_type: str) -> str:
    try:
        from googleapiclient.http import MediaFileUpload

        service = _get_service()
        user_folder_id = _get_or_create_user_folder(service, user_id)
        subfolder_name = FOLDER_MAP.get(file_type, "documents")
        subfolder_id = _find_or_create_folder(service, user_folder_id, subfolder_name)
        
        file_metadata = {"name": file_name, "parents": [subfolder_id]}
        media = MediaFileUpload(local_path, resumable=True)
        
        file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        logger.info(f"Uploaded: {file.get('id')}")
        return file.get("id")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

def download_file(drive_file_id: str, dest_path: str) -> str:
    try:
        from googleapiclient.http import MediaIoBaseDownload

        service = _get_service()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        request = service.files().get_media(fileId=drive_file_id)
        with io.FileIO(dest_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        
        logger.info(f"Downloaded: {dest_path}")
        return dest_path
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

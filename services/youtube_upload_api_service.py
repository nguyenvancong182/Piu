"""
YouTube Upload API Service for Piu Application

Handles YouTube video uploads via Google API.
"""

import os
import logging
from typing import Optional, Callable, Dict, List, Tuple


def upload_video_to_youtube(
    youtube_service,
    video_path: str,
    title: str,
    description: Optional[str],
    tags: List[str],
    privacy_status: str,
    category_id: str,
    progress_callback: Optional[Callable[[int], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None,
    stop_event=None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Upload video to YouTube using Google API.
    
    Args:
        youtube_service: YouTube API service object
        video_path: Path to video file
        title: Video title
        description: Video description (optional)
        tags: List of tags
        privacy_status: Privacy status (public, unlisted, private)
        category_id: YouTube category ID
        progress_callback: Optional callback for progress updates (0-100)
        log_callback: Optional callback for log messages
        stop_event: Optional threading event to check for cancellation
        
    Returns:
        Tuple of (success, video_id, error_message)
    """
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    
    worker_log_prefix = "[YouTubeUploadAPI]"
    
    if log_callback:
        log_callback(f"Bắt đầu tải lên: '{os.path.basename(video_path)}'")
        log_callback(f"Tiêu đề: '{title}'")
    
    logging.info(f"{worker_log_prefix} Bắt đầu upload video: '{os.path.basename(video_path)}'")
    
    # Check if file exists
    if not os.path.exists(video_path):
        error_msg = f"Tệp video không tồn tại: {os.path.basename(video_path)}"
        logging.error(f"{worker_log_prefix} {error_msg}")
        return False, None, error_msg
    
    # Check if cancelled
    if stop_event and stop_event.is_set():
        error_msg = "Đã dừng bởi người dùng trước khi upload."
        logging.info(f"{worker_log_prefix} {error_msg}")
        return False, None, error_msg
    
    try:
        # Build request body
        snippet = {
            'title': title,
            'categoryId': category_id
        }
        
        if description is not None:
            snippet['description'] = description
        
        if tags:
            snippet['tags'] = tags
        
        body = {
            'snippet': snippet,
            'status': { 
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False 
            }
        }
        
        # Create media upload
        media_body = MediaFileUpload(
            video_path, 
            chunksize=(1024*1024),  # 1MB chunks
            resumable=True
        )
        
        # Create upload request
        request = youtube_service.videos().insert(
            part=",".join(body.keys()), 
            body=body, 
            media_body=media_body
        )
        
        if log_callback:
            log_callback("Đang tải lên video...")
        
        # Upload with progress tracking
        response_from_api = None
        if progress_callback:
            progress_callback(0)
        
        while response_from_api is None:
            # Check for cancellation
            if stop_event and stop_event.is_set():
                error_msg = "Quá trình tải lên bị dừng bởi người dùng."
                logging.info(f"{worker_log_prefix} {error_msg}")
                return False, None, error_msg
            
            try:
                status, response_from_api = request.next_chunk()
                
                if status:
                    # Calculate and report progress
                    bytes_uploaded = status.resumable_progress
                    total_size = status.total_size
                    
                    if total_size > 0:
                        percent_complete = int((bytes_uploaded / total_size) * 100)
                        if progress_callback:
                            progress_callback(percent_complete)
                        
                        logging.debug(f"{worker_log_prefix} Upload progress: {percent_complete}%")
                        
            except HttpError as e_chunk:
                error_content_chunk = e_chunk.content.decode('utf-8', 'replace')
                
                # Check for quota exceeded
                if "uploadLimitExceeded" in error_content_chunk:
                    error_msg = "Đã vượt quá giới hạn upload của YouTube API."
                    logging.error(f"{worker_log_prefix} {error_msg}")
                    if log_callback:
                        log_callback(f"❌ {error_msg}")
                    return False, None, error_msg
                
                # Network error - retry
                logging.error(f"{worker_log_prefix} Lỗi khi upload chunk: {e_chunk}. Sẽ thử lại sau 5 giây.")
                if log_callback:
                    log_callback("Lỗi mạng khi đang upload, đang thử kết nối lại...")
                
                import time
                time.sleep(5)
                continue
        
        # Check response
        if response_from_api:
            video_id = response_from_api.get('id')
            if video_id:
                logging.info(f"{worker_log_prefix} Upload thành công! Video ID: {video_id}")
                if log_callback:
                    log_callback(f"✅ Tải lên video thành công! ID: {video_id}")
                    log_callback(f"Link video: https://youtu.be/{video_id}")
                return True, video_id, None
            else:
                error_msg = "Tải lên thành công nhưng không nhận được ID video."
                logging.warning(f"{worker_log_prefix} {error_msg}")
                return False, None, error_msg
        else:
            error_msg = "Tải lên không thành công hoặc không có phản hồi."
            logging.error(f"{worker_log_prefix} {error_msg}")
            return False, None, error_msg
            
    except HttpError as e_api:
        error_details = e_api.content.decode('utf-8', 'ignore')
        logging.error(f"{worker_log_prefix} Lỗi API: {error_details}", exc_info=True)
        
        # Parse specific errors
        if "uploadLimitExceeded" in error_details:
            error_msg = "⚠️ Bạn đã vượt quá giới hạn upload của YouTube API trong ngày hôm nay. Vui lòng thử lại sau."
        elif "unauthorized" in error_details.lower():
            error_msg = "⚠️ Lỗi xác thực với YouTube API. Vui lòng kiểm tra lại Google API Key trong Settings."
        else:
            error_msg = f"Lỗi API: {e_api.resp.status}"
        
        if log_callback:
            log_callback(f"❌ {error_msg}")
        
        return False, None, error_msg
        
    except Exception as e:
        error_msg = f"Lỗi không mong muốn: {e}"
        logging.error(f"{worker_log_prefix} {error_msg}", exc_info=True)
        if log_callback:
            log_callback(f"❌ {error_msg}")
        return False, None, error_msg


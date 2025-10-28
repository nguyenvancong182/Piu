"""
YouTube Upload Service for Piu Application

This service handles YouTube video uploads including thumbnails and playlists.
"""

import os
import logging
from typing import Optional, Callable, Dict


def upload_youtube_thumbnail(
    youtube_service,
    video_id: str,
    thumbnail_path: str,
    log_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Upload thumbnail for a YouTube video.
    
    Args:
        youtube_service: YouTube API service object
        video_id: YouTube video ID
        thumbnail_path: Path to thumbnail image file
        log_callback: Optional callback function to log messages (for UI updates)
        
    Returns:
        True if successful, False otherwise
    """
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    
    log_prefix = f"[YouTubeThumbnail_{video_id}]"
    
    # Validate input
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        logging.warning(f"{log_prefix} Đường dẫn thumbnail không hợp lệ hoặc file không tồn tại. Bỏ qua.")
        if log_callback:
            log_callback("⚠️ Thumbnail không hợp lệ. Bỏ qua.")
        return False
    
    logging.info(f"{log_prefix} Bắt đầu tải lên thumbnail từ: {os.path.basename(thumbnail_path)}")
    if log_callback:
        log_callback("🖼️ Đang tải lên thumbnail...")
    
    try:
        request = youtube_service.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path, mimetype='image/jpeg')
        )
        response = request.execute()
        logging.info(f"{log_prefix} Tải lên thumbnail thành công. Phản hồi: {response}")
        if log_callback:
            log_callback("✅ Tải lên thumbnail thành công.")
        return True
        
    except HttpError as e_thumb:
        error_msg = f"Lỗi khi tải lên thumbnail: {e_thumb.resp.status}. Có thể do tài khoản chưa được xác minh đầy đủ để dùng thumbnail tùy chỉnh."
        logging.error(f"{log_prefix} {error_msg}", exc_info=True)
        if log_callback:
            log_callback(f"❌ {error_msg}")
        return False
        
    except Exception as e_gen_thumb:
        logging.error(f"{log_prefix} Lỗi không mong muốn khi tải lên thumbnail: {e_gen_thumb}", exc_info=True)
        if log_callback:
            log_callback("❌ Lỗi không mong muốn khi tải lên thumbnail.")
        return False


def get_playlist_id_by_name(
    youtube_service,
    playlist_name: str,
    cache: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Get playlist ID by name from YouTube API.
    
    Args:
        youtube_service: YouTube API service object
        playlist_name: Name of the playlist to find
        cache: Optional dict to cache results (modified in place if provided)
        
    Returns:
        Playlist ID if found, None otherwise
    """
    # Check cache first if provided
    if cache and playlist_name in cache:
        logging.info(f"Đã tìm thấy Playlist ID trong cache: '{playlist_name}' -> '{cache[playlist_name]}'")
        return cache[playlist_name]

    logging.info(f"Đang tìm Playlist ID cho tên: '{playlist_name}' bằng API...")
    try:
        playlists_response = youtube_service.playlists().list(
            part="snippet",
            mine=True,
            maxResults=50  # Lấy tối đa 50 playlist mỗi lần
        ).execute()

        while playlists_response:
            for playlist in playlists_response.get("items", []):
                if playlist["snippet"]["title"].strip().lower() == playlist_name.strip().lower():
                    playlist_id = playlist["id"]
                    logging.info(f"Đã tìm thấy! Tên: '{playlist_name}', ID: '{playlist_id}'")
                    # Save to cache if provided
                    if cache is not None:
                        cache[playlist_name] = playlist_id
                    return playlist_id
            
            # Get next page if available
            if 'nextPageToken' in playlists_response:
                playlists_response = youtube_service.playlists().list(
                    part="snippet",
                    mine=True,
                    maxResults=50,
                    pageToken=playlists_response['nextPageToken']
                ).execute()
            else:
                break  # No more pages
        
        logging.warning(f"Không tìm thấy danh sách phát nào có tên: '{playlist_name}'")
        return None
        
    except Exception as e:
        logging.error(f"Lỗi khi lấy danh sách phát từ API: {e}")
        return None


def add_video_to_playlist(
    youtube_service,
    video_id: str,
    playlist_id: str,
    log_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Add a video to a YouTube playlist.
    
    Args:
        youtube_service: YouTube API service object
        video_id: YouTube video ID
        playlist_id: YouTube playlist ID
        log_callback: Optional callback function to log messages (for UI updates)
        
    Returns:
        True if successful, False otherwise
    """
    from googleapiclient.errors import HttpError
    
    try:
        logging.info(f"Đang thêm Video ID '{video_id}' vào Playlist ID '{playlist_id}'...")
        request_body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
        youtube_service.playlistItems().insert(
            part="snippet",
            body=request_body
        ).execute()
        logging.info("Thêm video vào danh sách phát thành công!")
        if log_callback:
            log_callback("✅ Đã thêm vào danh sách phát.")
        return True
        
    except HttpError as e:
        error_details = e.content.decode('utf-8', 'ignore')
        if "playlistNotFound" in error_details:
            logging.error(f"Lỗi: Playlist ID '{playlist_id}' không tồn tại.")
            if log_callback:
                log_callback("⚠️ Lỗi: Không tìm thấy danh sách phát để thêm vào.")
        elif "videoNotFound" in error_details:
            logging.error(f"Lỗi: Video ID '{video_id}' không tồn tại.")
            if log_callback:
                log_callback("⚠️ Lỗi: Không tìm thấy video để thêm vào danh sách phát.")
        else:
            logging.error(f"Lỗi API khi thêm video vào playlist: {e}")
            if log_callback:
                log_callback("⚠️ Lỗi API khi thêm video vào danh sách phát.")
        return False
        
    except Exception as e:
        logging.error(f"Lỗi không mong muốn khi thêm video vào playlist: {e}", exc_info=True)
        if log_callback:
            log_callback("⚠️ Lỗi không mong muốn khi thêm video vào danh sách phát.")
        return False


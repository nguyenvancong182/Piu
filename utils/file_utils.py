"""
File utility functions for Piu application.
Functions for processing files and directories.
"""

import os
import logging
import re


def prepare_batch_queue(folder_path):
    """
    Find all .srt and .txt files in a directory,
    then sort them by the number in the filename.
    
    Args:
        folder_path: Path to directory to scan
        
    Returns:
        List of sorted file paths, or empty list if error
    """
    if not os.path.isdir(folder_path):
        logging.warning(f"[Batch Mode] Thư mục không tồn tại: {folder_path}")
        return []

    supported_extensions = ('.srt', '.txt')
    files_with_numbers = []

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(supported_extensions):
            # Tìm số đầu tiên trong tên file
            match = re.search(r'\d+', filename)
            if match:
                # Lấy số tìm được và chuyển thành kiểu integer
                number = int(match.group())
                full_path = os.path.join(folder_path, filename)
                files_with_numbers.append((number, full_path))
            else:
                logging.info(f"[Batch Mode] Bỏ qua file không chứa số: {filename}")

    # Sắp xếp danh sách dựa trên số (phần tử đầu tiên của tuple)
    files_with_numbers.sort(key=lambda x: x[0])

    # Trả về danh sách chỉ chứa đường dẫn file đã được sắp xếp
    sorted_paths = [path for number, path in files_with_numbers]
    
    logging.info(f"[Batch Mode] Đã tìm thấy và sắp xếp được {len(sorted_paths)} file.")
    return sorted_paths


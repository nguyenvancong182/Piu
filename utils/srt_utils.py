"""
SRT parsing utilities for Piu application.

Functions for parsing SRT subtitle files and extracting timing information.
"""

import os
import re
import logging
from typing import List, Dict


def parse_srt_for_slideshow_timing(srt_file_path: str) -> List[Dict]:
    """
    Parse SRT file to extract start and end times for each subtitle block.
    Uses the parse_timecode function from helpers.
    
    Args:
        srt_file_path: Path to .srt file
        
    Returns:
        List of dictionaries containing:
        {'original_index': int, 'start_ms': int, 'end_ms': int, 'duration_ms': int}
        Returns empty list on error or no subtitles found
    """
    from utils.helpers import parse_timecode
    
    subtitles = []
    if not srt_file_path or not os.path.exists(srt_file_path):
        logging.warning(f"[ParseSRTSlideshow] SRT file doesn't exist or path is empty: {srt_file_path}")
        return subtitles

    try:
        with open(srt_file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        # Regex to match complete SRT subtitle block
        srt_block_pattern = re.compile(
            r"(\d+)\s*[\r\n]+"  # Index
            r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*[\r\n]+"  # Timecodes
            r"((?:.|\n|\r)*?)"  # Text content (non-greedy, including newlines)
            # Lookahead to stop before next block or end of file
            r"(?=\n\s*\n\d+\s*[\r\n]+|\n\s*\d+\s*[\r\n]+\d{2}:\d{2}:\d{2}[,.]\d{3}|\Z)",
            re.MULTILINE
        )

        matches = list(srt_block_pattern.finditer(content))
        logging.info(f"[ParseSRTSlideshow] Found {len(matches)} subtitle blocks in file '{os.path.basename(srt_file_path)}'.")

        for match_obj in matches: 
            try:
                index_str = match_obj.group(1)
                start_tc_str = match_obj.group(2).replace('.', ',') 
                end_tc_str = match_obj.group(3).replace('.', ',')   
                
                start_ms = parse_timecode(start_tc_str) 
                end_ms = parse_timecode(end_tc_str)     
                
                if end_ms > start_ms:
                    subtitles.append({
                        'original_index': int(index_str), 
                        'start_ms': start_ms,
                        'end_ms': end_ms,
                        'duration_ms': end_ms - start_ms
                        # 'text': text_cleaned_for_timing # Optional, if function only gets timing then no text needed
                    })
                else:
                    logging.warning(f"[ParseSRTSlideshow] Subtitle block #{index_str} has invalid time: {start_tc_str} --> {end_tc_str}")
            except Exception as e_block:
                error_context_text = match_obj.group(0)[:100] 
                logging.error(f"[ParseSRTSlideshow] Error processing subtitle block (near: '{error_context_text}...'): {e_block}", exc_info=False) 
                continue 
                
    except Exception as e_file:
        logging.error(f"[ParseSRTSlideshow] Critical error parsing SRT file '{srt_file_path}': {e_file}", exc_info=True)
    
    if subtitles:
        subtitles.sort(key=lambda x: x['start_ms']) 
        logging.info(f"[ParseSRTSlideshow] Parsed and sorted {len(subtitles)} valid subtitle blocks.")
    else:
        logging.warning(f"[ParseSRTSlideshow] Could not parse any valid subtitle blocks from file '{os.path.basename(srt_file_path)}'.")
        
    return subtitles


def format_srt_data_to_string(srt_data_content):
    """
    Convert SRT data list (dictionaries) to complete SRT string.
    
    Args:
        srt_data_content: List of dictionaries with SRT block data
        
    Returns:
        Complete SRT formatted string
    """
    if not srt_data_content:
        return ""
    
    from utils.helpers import ms_to_tc
    
    srt_string_output = []
    for i, block in enumerate(srt_data_content):
        index = block.get('index', i + 1)  # Use existing index or default to i+1
        start_str = block.get('start_str', ms_to_tc(block.get('start_ms', 0)))
        end_str = block.get('end_str', ms_to_tc(block.get('end_ms', 0)))
        text = block.get('text', '')
        
        srt_string_output.append(str(index))
        srt_string_output.append(f"{start_str} --> {end_str}")
        srt_string_output.append(text)
        srt_string_output.append("")  # Empty line between blocks
    
    # Join all parts, ensuring there's an empty line at the end if there's content
    final_str = "\n".join(srt_string_output)
    return final_str  # strip() and \n\n will be handled by caller if needed


def extract_dialogue_from_srt_string(text_content):
    """
    Extract only dialogue text from a string that may contain SRT formatting.
    If the string doesn't have SRT format, return the original cleaned string.
    
    Args:
        text_content: String that may contain SRT format
        
    Returns:
        Plain dialogue text without SRT formatting
    """
    # Quick check if there are SRT indicators
    if "-->" not in text_content or not re.search(r'\d{2}:\d{2}:\d{2}', text_content):
        # If no indicators, treat as plain text and return
        return ' '.join(text_content.strip().split())
    
    dialogue_parts = []
    # Regex to find SRT blocks and capture only the text part
    srt_block_pattern = re.compile(
        r"\d+\s*[\r\n]+"
        r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}\s*[\r\n]+"
        r"((?:.|\n|\r)*?)"  # Group to capture (group 1)
        r"(?=\n\s*\n\d+|\Z)",  # Lookahead to not consume next block
        re.MULTILINE
    )
    
    matches = list(srt_block_pattern.finditer(text_content))
    
    # If SRT blocks found, extract only dialogue
    if matches:
        logging.info(f"[ExtractDialogue] Detected {len(matches)} SRT blocks. Extracting dialogue only.")
        for match in matches:
            # Get text group, remove HTML/XML tags and extra whitespace
            dialogue_text = match.group(1).strip()
            cleaned_text = re.sub(r'<[^>]+>', '', dialogue_text)
            # Replace newlines with spaces and merge whitespace
            cleaned_text = ' '.join(cleaned_text.split())
            if cleaned_text:
                dialogue_parts.append(cleaned_text)
        
        # Join all dialogue into a single string
        return " ".join(dialogue_parts)
    else:
        # If no SRT blocks found, return original cleaned text
        logging.info("[ExtractDialogue] No SRT blocks found. Returning original cleaned text.")
        return ' '.join(text_content.strip().split())


def write_srt(file_handle, segments):
    """
    Write segments in SRT format to file handle.
    
    Args:
        file_handle: Open file handle to write to
        segments: List of dictionaries with 'start', 'end', 'text' keys
    """
    from utils.helpers import format_timestamp
    
    for i, segment in enumerate(segments):
        start = format_timestamp(segment['start'], separator=',')
        end = format_timestamp(segment['end'], separator=',')
        text = segment['text'].strip().replace('-->', '->')  # Avoid error with '-->' in text
        file_handle.write(f"{i + 1}\n")
        file_handle.write(f"{start} --> {end}\n")
        file_handle.write(f"{text}\n\n")


def write_vtt(file_handle, segments):
    """
    Write segments in WebVTT format to file handle.
    
    Args:
        file_handle: Open file handle to write to
        segments: List of dictionaries with 'start', 'end', 'text' keys
    """
    from utils.helpers import format_timestamp
    
    file_handle.write("WEBVTT\n\n")
    for i, segment in enumerate(segments):
        start = format_timestamp(segment['start'], separator='.')
        end = format_timestamp(segment['end'], separator='.')
        text = segment['text'].strip().replace('-->', '->')
        file_handle.write(f"{start} --> {end}\n")
        file_handle.write(f"{text}\n\n")

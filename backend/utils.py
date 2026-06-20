"""
CodeTribunal - Utility Functions
Helper functions for the application
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from .schemas import ProceedingEntry, AgentRole
from .config import settings


def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(settings.LOG_FILE),
            logging.StreamHandler()
        ]
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)


def sanitize_code_content(code_content: str) -> str:
    """
    Sanitize code content before processing
    """
    # Remove any potentially dangerous content if needed
    sanitized = code_content.strip()
    return sanitized


def detect_language_from_extension(filename: str) -> str:
    """
    Detect programming language from file extension
    """
    language_map = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.go': 'Go',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.cs': 'C#',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.html': 'HTML',
        '.css': 'CSS',
        '.json': 'JSON',
        '.xml': 'XML',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.sh': 'Shell',
        '.sql': 'SQL',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.rs': 'Rust',
        '.scala': 'Scala',
        '.lua': 'Lua',
        '.pl': 'Perl',
        '.r': 'R',
        '.dart': 'Dart',
        '.m': 'Objective-C',
        '.mm': 'Objective-C++'
    }
    
    ext = '.' + filename.split('.')[-1].lower()
    return language_map.get(ext, 'Unknown')


def detect_language_from_content(code_content: str) -> str:
    """
    Detect programming language from code content heuristics
    """
    content_lower = code_content.lower()
    
    # Common language identifiers
    lang_identifiers = {
        'Python': ['import ', 'def ', 'class ', 'print(', 'lambda '],
        'JavaScript': ['function', 'var ', 'let ', 'const ', 'console.log'],
        'Java': ['public class', 'private ', 'protected ', 'System.out.println'],
        'C++': ['#include', 'using namespace', 'cout <<'],
        'C': ['#include', 'int main', 'printf('],
        'Go': ['package ', 'import ', 'func '],
        'C#': ['using System', 'namespace ', 'class ', 'Console.WriteLine'],
        'PHP': ['<?php', '<?', 'echo ', '$'],
        'Ruby': ['def ', 'puts ', 'require ', '#'],
        'TypeScript': ['interface ', 'type ', 'import ', 'export '],
        'Swift': ['import ', 'var ', 'let ', 'func ', 'class '],
        'Kotlin': ['fun ', 'val ', 'var ', 'class ', 'import '],
        'Rust': ['fn ', 'mod ', 'use ', 'impl ', 'struct '],
        'Scala': ['object ', 'def ', 'val ', 'var ', 'class '],
        'Lua': ['function ', 'local ', 'require', 'print'],
        'Perl': ['#!/usr/bin/perl', 'use ', 'sub ', '@', '%'],
        'R': ['library(', 'data.frame', 'function(', 'plot('],
        'Dart': ['void main', 'import ', 'class ', 'var ', 'final '],
        'SQL': ['SELECT ', 'INSERT INTO', 'UPDATE ', 'DELETE FROM', 'CREATE TABLE'],
        'Shell': ['#!/bin/bash', '#!/bin/sh', 'echo ', 'if [', 'for '],
        'HTML': ['<html>', '<head>', '<body>', '<div', '<span'],
        'CSS': ['{', '}', 'color:', 'margin:', 'padding:']
    }
    
    scores = {}
    for lang, keywords in lang_identifiers.items():
        score = sum(1 for keyword in keywords if keyword.lower() in content_lower)
        scores[lang] = score
    
    # Return the language with highest score, or 'Unknown' if no clear match
    detected_lang = max(scores, key=scores.get)
    return detected_lang if scores[detected_lang] > 0 else 'Unknown'


def calculate_complexity_score(code_content: str) -> int:
    """
    Calculate a basic complexity score for the code
    """
    lines = len(code_content.split('\n'))
    complexity_score = min(10, max(1, lines // 50))  # Simplified complexity calculation
    
    # Additional complexity factors
    if 'for ' in code_content or 'while ' in code_content:
        complexity_score += code_content.count('for ') + code_content.count('while ')
    if 'if ' in code_content:
        complexity_score += code_content.count('if ') // 3  # Count conditional complexity
    
    return min(10, complexity_score)


def extract_security_patterns(code_content: str) -> List[str]:
    """
    Extract potential security patterns from code
    """
    security_patterns = []
    
    # Regex patterns for common security issues
    patterns = [
        (r'password\s*=\s*["\'][^"\']*["\']', 'Hardcoded password'),
        (r'(eval\(|exec\()', 'Dangerous eval/exec usage'),
        (r"(SELECT|INSERT|UPDATE|DELETE)\s+.+\s+WHERE\s+.+=\s*['\"].*['\"]", 'Potential SQL injection'),
        (r'os\.system\(|subprocess\.call\(|subprocess\.run\(', 'OS command execution'),
        (r'<script>', 'Potential XSS in HTML'),
        (r'pickle\.', 'Unsafe pickle usage'),
        (r'register_shutdown_function|assert\(|create_function', 'Potentially dangerous PHP functions'),
        (r'\$_GET|\$_POST|\$_REQUEST', 'Direct use of user input'),
        (r'innerHTML|document\.write', 'Potential DOM XSS'),
    ]
    
    for pattern, description in patterns:
        matches = re.findall(pattern, code_content, re.IGNORECASE)
        if matches:
            security_patterns.append(f"{description}: {len(matches)} occurrences")
    
    return security_patterns


def format_timestamp(timestamp: datetime) -> str:
    """
    Format a datetime object to a readable string
    """
    return timestamp.strftime('%Y-%m-%d %H:%M:%S')


def format_agent_response(agent_role: AgentRole, tag: str, message: str, round_number: int) -> str:
    """
    Format an agent's response for display
    """
    timestamp = format_timestamp(datetime.now())
    return f"[{timestamp}] {agent_role.value} [{tag}, Round {round_number}]: {message}"


def merge_dicts(base_dict: Dict[str, Any], override_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries, with override_dict taking precedence
    """
    result = base_dict.copy()
    
    for key, value in override_dict.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def truncate_text(text: str, max_length: int = 200) -> str:
    """
    Truncate text to a maximum length, adding ellipsis if truncated
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def validate_token_usage(input_tokens: int, output_tokens: int, model_name: str) -> bool:
    """
    Validate token usage against limits if configured
    """
    # In a real implementation, this would check against actual token limits
    # For now, just return True
    return True


def generate_case_title(code_content: str, language: str) -> str:
    """
    Generate a case title based on the code content and language
    """
    # Try to extract a function or class name from the code
    lines = code_content.split('\n')
    
    for line in lines[:20]:  # Check first 20 lines
        line = line.strip()
        
        # Look for function definitions
        func_match = re.match(r'def\s+(\w+)\s*\(', line) or \
                    re.match(r'function\s+(\w+)\s*\(', line) or \
                    re.match(r'func\s+(\w+)\s*\(', line)  # Go function
        
        if func_match:
            return f"The People vs. {func_match.group(1)}()"
        
        # Look for class definitions
        class_match = re.match(r'class\s+(\w+)', line)
        if class_match:
            return f"The People vs. {class_match.group(1)}"
    
    # If no specific function/class found, use generic title
    lines_count = len(code_content.split('\n'))
    return f"Code Review Case - {language} ({lines_count} lines)"
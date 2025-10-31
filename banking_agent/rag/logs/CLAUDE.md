# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) about the logs directory in the RAG module.

## Directory Overview

This directory contains Cognee-generated log files that track RAG operations including document ingestion, search queries, database operations, and system events. These logs are automatically created by the Cognee framework during runtime.

## Log File Format

### Naming Convention
- Pattern: `YYYY-MM-DD_HH-MM-SS.log`
- Example: `2025-10-30_12-21-17.log`
- Each log file corresponds to a single session/run of Cognee operations

### Log Entry Structure
```
TIMESTAMP [LEVEL] Message key1=value1 key2=value2 [module.name]
```

Example:
```
2025-10-30T12:21:19.224297 [INFO] Logging initialized python_version=3.12.0 structlog_version=25.5.0 cognee_version=0.3.8 [cognee.shared.logging_utils]
```

### Log Levels
- `[INFO]`: Normal operational messages (initialization, completion, progress)
- `[WARNING]`: Non-critical issues (missing optional dependencies, deprecated features)
- `[ERROR]`: Errors that need attention (failed operations, exceptions)
- `[DEBUG]`: Detailed diagnostic information (only in debug mode)

## What Gets Logged

### System Initialization (Lines 1-3 typically)
```
Log file created at: <path>
Logging initialized python_version=... cognee_version=... database_path=...
Database storage: <path>
```

Key information:
- Python version
- Cognee version (currently 0.3.8)
- OS information
- Database paths: `/rag/cognee/.cognee_system/databases`
- Vector config: `lancedb`
- Relational config: `cognee_db`

### Database Operations
- SQLite connection events
- SQL queries (SELECT, INSERT, UPDATE)
- User authentication queries (`default_user@example.com`)
- Transaction operations (commit, rollback)

### Document Processing
- Document ingestion progress
- Embedding generation
- Knowledge graph creation
- Chunking operations

### Search Operations
- Search queries executed
- Results retrieved
- Ranking and filtering operations

### Warnings
Common warnings you may see:
- `Failed to import protego` - Optional web scraping dependency
- `Failed to import playwright` - Optional browser automation dependency
- These warnings are **normal** and don't affect RAG functionality for PDF processing

## Using Logs for Debugging

### Check Last Operation Status
```bash
# View the most recent log file
ls -t | head -1 | xargs cat
```

### Find Errors
```bash
# Search for errors across all logs
grep "\[ERROR" *.log
```

### Track Document Ingestion
```bash
# Look for ingestion-related messages
grep -i "ingest\|add\|cognify" *.log
```

### Monitor Search Performance
```bash
# Find search operations and timing
grep -i "search" *.log
```

### View System Configuration
```bash
# Check initialization to see current config
head -20 <latest-log-file>
```

## Important Notes

### Do NOT Modify Log Files
- These files are **generated** by Cognee and should not be edited
- They are for **reference and debugging only**
- Deleting them won't affect RAG functionality (new ones will be created)

### Log Rotation
- Cognee creates a new log file for each session
- Old logs are NOT automatically deleted
- You may want to periodically clean up old logs to save disk space:
  ```bash
  # Keep only logs from last 7 days (example)
  find . -name "*.log" -mtime +7 -delete
  ```

### Performance Considerations
- Verbose logging can impact performance slightly
- In production, consider adjusting Cognee's log level
- Log file size grows with the number of operations

### Privacy and Security
- Logs may contain:
  - File paths
  - SQL queries (but not sensitive data values)
  - System information
  - User email (`default_user@example.com`)
- **Do NOT commit logs to version control** (should be in .gitignore)

## Common Log Patterns

### Successful Ingestion
```
[INFO] Logging initialized...
[INFO] Database storage: ...
[INFO] Document added: <filename>
[INFO] Cognify completed
```

### Failed Ingestion
```
[ERROR] Failed to process document: <error details>
[ERROR] Exception during cognify: <stack trace>
```

### Successful Search
```
[INFO] Search query: <query>
[INFO] Found <N> results
[INFO] Results ranked by relevance
```

### Database Issues
```
[ERROR] Database connection failed
[ERROR] SQLite error: <error message>
```

## Troubleshooting with Logs

### Problem: Empty search results
**Check logs for**:
- Whether documents were successfully ingested
- Search query execution
- Database connection issues

### Problem: Ingestion failures
**Check logs for**:
- File reading errors
- Memory issues
- Database write failures
- Embedding generation errors

### Problem: Slow performance
**Check logs for**:
- Large number of database operations
- Long-running queries
- Memory warnings

## Log Configuration

The Cognee logging system is configured in `cognee/shared/logging_utils.py` (in the reference cognee/ directory). Default settings:
- Format: Structured logging with key-value pairs
- Output: File in logs/ directory
- Level: INFO (can be changed to DEBUG for more detail)

To modify logging behavior, configure before initializing Cognee in ingest.py or retrieval.py.

## File Retention Recommendations

- **Development**: Keep logs for debugging, clean up periodically
- **Production**: Implement log rotation (keep last N days or last N files)
- **Storage**: Each log file is typically 10-100 KB for normal operations

## Summary

- **Purpose**: Debug and monitor RAG operations
- **Generated by**: Cognee framework automatically
- **Do NOT**: Modify or commit to version control
- **Do**: Use for debugging, troubleshooting, and understanding system behavior
- **Clean up**: Periodically remove old logs to save space

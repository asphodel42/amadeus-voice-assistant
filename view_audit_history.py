#!/usr/bin/env python3
"""
Audit History Viewer

CLI tool for viewing and analyzing audit logs.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from amadeus.adapters.persistence.audit import SQLiteAuditAdapter


def print_separator(char="=", length=70):
    """Print a separator line."""
    print(char * length)


def print_statistics(audit: SQLiteAuditAdapter):
    """Print statistics about the audit log."""
    print_separator()
    print("📊 AUDIT LOG STATISTICS")
    print_separator()
    print()
    
    stats = audit.get_statistics()
    
    print(f"Total Events: {stats['total_events']}")
    print(f"First Event:  {stats['first_event']}")
    print(f"Last Event:   {stats['last_event']}")
    print()
    
    print("Events by Type:")
    print("-" * 40)
    for event_type, count in sorted(stats['events_by_type'].items(), key=lambda x: -x[1]):
        percentage = (count / stats['total_events'] * 100) if stats['total_events'] > 0 else 0
        print(f"  {event_type:25s}: {count:5d} ({percentage:5.1f}%)")
    print()
    
    print("Events by Actor:")
    print("-" * 40)
    for actor, count in stats['events_by_actor'].items():
        print(f"  {actor:25s}: {count:5d}")
    print()
    
    if stats['events_per_day']:
        print("Recent Activity (last 7 days):")
        print("-" * 40)
        for date, count in sorted(stats['events_per_day'].items(), reverse=True):
            print(f"  {date}: {count} events")
        print()


def print_command_history(audit: SQLiteAuditAdapter, limit: int = 20):
    """Print recent command history."""
    print_separator()
    print("📜 COMMAND HISTORY")
    print_separator()
    print()
    
    commands = audit.get_command_history(limit=limit)
    
    if not commands:
        print("No commands found.")
        return
    
    for i, cmd in enumerate(commands, 1):
        status_icon = {
            "completed": "✅",
            "denied": "🚫",
            "pending": "⏳",
        }.get(cmd.get("status", "pending"), "❓")
        
        print(f"{i}. {status_icon} [{cmd['timestamp']}]")
        print(f"   Command: {cmd['raw_text']}")
        if cmd.get('intent_type'):
            print(f"   Intent:  {cmd['intent_type']}")
        print(f"   Status:  {cmd['status']}")
        print()


def print_voice_interactions(audit: SQLiteAuditAdapter, limit: int = 20):
    """Print voice interactions with NLU results."""
    print_separator()
    print("🎤 VOICE INTERACTIONS")
    print_separator()
    print()
    
    interactions = audit.get_voice_interactions(limit=limit)
    
    if not interactions:
        print("No voice interactions found.")
        return
    
    for i, interaction in enumerate(interactions, 1):
        print(f"{i}. [{interaction['timestamp']}]")
        if interaction.get('raw_text'):
            print(f"   🗣️  User said: {interaction['raw_text']}")
        if interaction.get('intent_type'):
            print(f"   🧠 Recognized: {interaction['intent_type']}")
        
        metadata = interaction.get('metadata', {})
        if 'confidence' in metadata:
            print(f"   📊 Confidence: {metadata['confidence']:.2%}")
        if metadata.get('is_unknown'):
            print(f"   ❓ Unknown intent")
        
        print()


def search_logs(audit: SQLiteAuditAdapter, search_text: str, limit: int = 20):
    """Search through audit logs."""
    print_separator()
    print(f"🔍 SEARCH RESULTS FOR: '{search_text}'")
    print_separator()
    print()
    
    results = audit.search_events(search_text, limit=limit)
    
    if not results:
        print("No matching events found.")
        return
    
    print(f"Found {len(results)} matching events:")
    print()
    
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result['timestamp']}] {result['event_type']}")
        data = result.get('data', {})
        if data.get('command_request'):
            print(f"   Command: {data['command_request'].get('raw_text')}")
        if data.get('plan'):
            print(f"   Intent:  {data['plan'].get('intent_type')}")
        print()


def verify_integrity(audit: SQLiteAuditAdapter):
    """Verify audit log integrity."""
    print_separator()
    print("🔒 INTEGRITY VERIFICATION")
    print_separator()
    print()
    
    print("Verifying hash chain...")
    is_valid = audit.verify_integrity()
    
    if is_valid:
        print("✅ PASSED: Audit log integrity is intact")
        print("   No tampering detected")
    else:
        print("❌ FAILED: Audit log has been tampered with!")
        print("   Hash chain is broken")
    
    print()


def export_logs(audit: SQLiteAuditAdapter, output_file: str, limit: int = 10000):
    """Export logs to JSON file."""
    print_separator()
    print("💾 EXPORTING LOGS")
    print_separator()
    print()
    
    print(f"Exporting to: {output_file}")
    print(f"Limit: {limit} events")
    print()
    
    count = audit.export_to_json(output_file, limit=limit)
    
    print(f"✅ Exported {count} events successfully")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Amadeus Audit History Viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View statistics
  python view_audit_history.py --stats
  
  # View command history
  python view_audit_history.py --history
  
  # View voice interactions
  python view_audit_history.py --voice
  
  # Search logs
  python view_audit_history.py --search "open calculator"
  
  # Verify integrity
  python view_audit_history.py --verify
  
  # Export to JSON
  python view_audit_history.py --export audit_backup.json
        """,
    )
    
    parser.add_argument(
        "--db",
        type=str,
        default="~/.amadeus/audit.db",
        help="Path to audit database (default: ~/.amadeus/audit.db)",
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics",
    )
    
    parser.add_argument(
        "--history",
        action="store_true",
        help="Show command history",
    )
    
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Show voice interactions",
    )
    
    parser.add_argument(
        "--search",
        type=str,
        help="Search logs for text",
    )
    
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify integrity of audit log",
    )
    
    parser.add_argument(
        "--export",
        type=str,
        metavar="FILE",
        help="Export logs to JSON file",
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Limit number of results (default: 20)",
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all information (stats + history + voice)",
    )
    
    args = parser.parse_args()
    
    # Check if database exists
    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        print(f"❌ Error: Database not found at {db_path}")
        print()
        print("Run the assistant first to create the database:")
        print("  python -m amadeus.app.main --voice")
        sys.exit(1)
    
    # Initialize audit adapter
    try:
        audit = SQLiteAuditAdapter(db_path=args.db)
    except Exception as e:
        print(f"❌ Error: Could not open database: {e}")
        sys.exit(1)
    
    # If no options specified, show help
    if not any([args.stats, args.history, args.voice, args.search, 
                args.verify, args.export, args.all]):
        parser.print_help()
        sys.exit(0)
    
    # Execute requested actions
    if args.all:
        print_statistics(audit)
        print()
        print_command_history(audit, limit=args.limit)
        print()
        print_voice_interactions(audit, limit=args.limit)
        print()
        verify_integrity(audit)
    else:
        if args.stats:
            print_statistics(audit)
        
        if args.history:
            print_command_history(audit, limit=args.limit)
        
        if args.voice:
            print_voice_interactions(audit, limit=args.limit)
        
        if args.search:
            search_logs(audit, args.search, limit=args.limit)
        
        if args.verify:
            verify_integrity(audit)
        
        if args.export:
            export_logs(audit, args.export, limit=10000)
    
    print_separator()


if __name__ == "__main__":
    main()

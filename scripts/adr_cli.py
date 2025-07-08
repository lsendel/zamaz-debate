#!/usr/bin/env python3
"""
CLI tool for managing Architectural Decision Records
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from services.adr_service import ADRService, ADRStatus


def list_adrs(args):
    """List all ADRs"""
    adr_service = ADRService()
    adrs = adr_service.get_all_adrs()
    
    if not adrs:
        print("No ADRs found.")
        return
    
    print(f"\n{'Number':<8} {'Status':<12} {'Title':<50} {'Created'}")
    print("-" * 90)
    
    for adr in adrs:
        created = datetime.fromisoformat(adr['created']).strftime('%Y-%m-%d')
        print(f"{adr['number']:<8} {adr['status']:<12} {adr['title'][:50]:<50} {created}")
    
    print(f"\nTotal: {len(adrs)} ADRs")


def show_adr(args):
    """Show a specific ADR"""
    adr_service = ADRService()
    adr = adr_service.get_adr(args.number)
    
    if not adr:
        print(f"ADR {args.number} not found.")
        return
    
    # Read and display the file
    adr_file = adr_service.adr_dir / adr['filename']
    if adr_file.exists():
        with open(adr_file, 'r') as f:
            print(f.read())
    else:
        print(f"ADR file not found: {adr['filename']}")


def create_adr(args):
    """Create a new ADR"""
    adr_service = ADRService()
    
    # Parse consequences
    consequences = {
        "positive": args.positive.split(',') if args.positive else ["To be documented"],
        "negative": args.negative.split(',') if args.negative else ["To be assessed"],
        "neutral": args.neutral.split(',') if args.neutral else ["No significant neutral impacts"]
    }
    
    filename = adr_service.create_adr(
        title=args.title,
        context=args.context,
        decision=args.decision,
        consequences=consequences,
        implementation_details=args.implementation
    )
    
    print(f"Created ADR: {filename}")
    
    # Show the created ADR
    number = filename.split('-')[0]
    print(f"\nView with: python scripts/adr_cli.py show {number}")


def update_status(args):
    """Update ADR status"""
    adr_service = ADRService()
    
    # Convert string to enum
    try:
        status = ADRStatus[args.status.upper()]
    except KeyError:
        print(f"Invalid status: {args.status}")
        print(f"Valid statuses: {', '.join([s.value for s in ADRStatus])}")
        return
    
    if adr_service.update_adr_status(args.number, status):
        print(f"Updated ADR {args.number} status to {status.value}")
    else:
        print(f"Failed to update ADR {args.number} - not found")


def main():
    parser = argparse.ArgumentParser(description="Manage Architectural Decision Records")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all ADRs')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show a specific ADR')
    show_parser.add_argument('number', help='ADR number (e.g., 001)')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new ADR')
    create_parser.add_argument('title', help='ADR title')
    create_parser.add_argument('context', help='Context for the decision')
    create_parser.add_argument('decision', help='The decision made')
    create_parser.add_argument('--positive', help='Positive consequences (comma-separated)')
    create_parser.add_argument('--negative', help='Negative consequences (comma-separated)')
    create_parser.add_argument('--neutral', help='Neutral consequences (comma-separated)')
    create_parser.add_argument('--implementation', help='Implementation details')
    
    # Update status command
    status_parser = subparsers.add_parser('status', help='Update ADR status')
    status_parser.add_argument('number', help='ADR number')
    status_parser.add_argument('status', choices=['proposed', 'accepted', 'deprecated', 'superseded'],
                             help='New status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    if args.command == 'list':
        list_adrs(args)
    elif args.command == 'show':
        show_adr(args)
    elif args.command == 'create':
        create_adr(args)
    elif args.command == 'status':
        update_status(args)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
VPS Infrastructure Deployment Script
Python version of the bash deployment script using uv
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Optional

# Color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def print_colored(message: str, color: str = Colors.NC):
    print(f"{color}{message}{Colors.NC}")

def run_command(command: str, cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        print_colored(f"❌ Command failed: {command}", Colors.RED)
        if e.stderr:
            print_colored(f"   Error: {e.stderr}", Colors.RED)
        if check:
            sys.exit(1)
        return e

def check_prerequisites():
    """Check if required tools are installed"""
    tools = ['ansible-playbook']
    
    for tool in tools:
        try:
            result = run_command(f"command -v {tool}")
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, f"command -v {tool}")
        except subprocess.CalledProcessError:
            print_colored(f"❌ {tool.replace('-', ' ').title()} is required but not installed.", Colors.RED)
            sys.exit(1)

def ansible_syntax_check(environment: str, ansible_dir: Path):
    """Check Ansible playbook syntax"""
    print_colored("📋 Checking Ansible syntax...", Colors.BLUE)
    inventory_file = ansible_dir / f"inventories/{environment}.yml"
    
    if not inventory_file.exists():
        print_colored(f"❌ Ansible inventory file not found: {inventory_file}", Colors.RED)
        sys.exit(1)
    
    run_command(f"ansible-playbook playbooks/site.yml --syntax-check -i inventories/{environment}.yml", cwd=ansible_dir)

def ansible_check(environment: str, ansible_dir: Path):
    """Run Ansible in check mode (dry-run)"""
    print_colored("🧪 Running Ansible dry-run...", Colors.BLUE)
    inventory_file = ansible_dir / f"inventories/{environment}.yml"
    
    if not inventory_file.exists():
        print_colored(f"❌ Ansible inventory file not found: {inventory_file}", Colors.RED)
        sys.exit(1)
    
    run_command(f"ansible-playbook playbooks/site.yml --check -i inventories/{environment}.yml", cwd=ansible_dir)

def ansible_deploy(environment: str, ansible_dir: Path):
    """Deploy with Ansible"""
    print_colored("🚀 Deploying configuration with Ansible...", Colors.BLUE)
    inventory_file = ansible_dir / f"inventories/{environment}.yml"
    
    if not inventory_file.exists():
        print_colored(f"❌ Ansible inventory file not found: {inventory_file}", Colors.RED)
        sys.exit(1)
    
    run_command(f"ansible-playbook playbooks/site.yml -i inventories/{environment}.yml", cwd=ansible_dir)

def ansible_cleanup(environment: str, ansible_dir: Path):
    """Run cleanup playbook"""
    print_colored("🧹 Running cleanup playbook...", Colors.YELLOW)
    
    cleanup_playbook = ansible_dir / "playbooks/cleanup.yml"
    inventory_file = ansible_dir / f"inventories/{environment}.yml"
    
    if not inventory_file.exists():
        print_colored(f"❌ Ansible inventory file not found: {inventory_file}", Colors.RED)
        sys.exit(1)
    
    if cleanup_playbook.exists():
        run_command(f"ansible-playbook playbooks/cleanup.yml -i inventories/{environment}.yml", 
                   cwd=ansible_dir, check=False)
    else:
        print_colored("⚠️ No cleanup playbook found, skipping cleanup", Colors.YELLOW)

def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description='VPS Infrastructure Deployment Script')
    parser.add_argument('environment', nargs='?', default='production', 
                       help='Environment to deploy (default: production)')
    parser.add_argument('action', nargs='?', default='check', 
                       choices=['check', 'plan', 'apply', 'cleanup'],
                       help='Action to perform (default: check)')
    
    args = parser.parse_args()
    
    print_colored(f"🚀 Starting deployment for environment: {args.environment}", Colors.BLUE)
    
    # Get project root directory
    project_root = Path(__file__).parent.parent.parent
    ansible_dir = project_root / "ansible"
    
    # Check if ansible directory exists
    if not ansible_dir.exists():
        print_colored(f"❌ Ansible directory not found: {ansible_dir}", Colors.RED)
        print_colored("💡 This script requires an ansible directory with playbook configuration", Colors.YELLOW)
        sys.exit(1)
    
    # Check prerequisites
    check_prerequisites()
    
    # Perform the requested action
    if args.action == 'check':
        ansible_syntax_check(args.environment, ansible_dir)
    elif args.action == 'plan':
        ansible_check(args.environment, ansible_dir)
    elif args.action == 'apply':
        ansible_deploy(args.environment, ansible_dir)
    elif args.action == 'cleanup':
        ansible_cleanup(args.environment, ansible_dir)
    
    print_colored("✅ Operation completed successfully!", Colors.GREEN)

if __name__ == "__main__":
    main()
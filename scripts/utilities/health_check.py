#!/usr/bin/env python3
"""
Infrastructure Health Check Script
Python version of the bash health check script using uv
"""

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

def run_ansible_command(command: str, inventory_file: Path, cwd: Optional[Path] = None) -> bool:
    """Run an Ansible command and return success status"""
    full_command = f"ansible {command} -i {inventory_file.name}"
    
    try:
        result = subprocess.run(
            full_command,
            shell=True,
            cwd=cwd,
            text=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"❌ Command failed: {full_command}", Colors.RED)
        return False

def check_connectivity(environment: str, ansible_dir: Path) -> bool:
    """Check if servers are reachable"""
    print_colored("📡 Checking server connectivity...", Colors.BLUE)
    
    inventory_file = ansible_dir / f"inventories/{environment}.yml"
    
    if not inventory_file.exists():
        print_colored(f"❌ Inventory file not found: {inventory_file}", Colors.RED)
        return False
    
    return run_ansible_command("all -m ping", inventory_file, ansible_dir)

def check_system_resources(environment: str, ansible_dir: Path) -> bool:
    """Check system resources on all servers"""
    print_colored("💾 Checking system resources...", Colors.BLUE)
    
    inventory_file = ansible_dir / f"inventories/{environment}.yml"
    
    if not inventory_file.exists():
        print_colored(f"❌ Inventory file not found: {inventory_file}", Colors.RED)
        return False
    
    commands = [
        ('disk usage', 'all -m shell -a "df -h | head -5"'),
        ('memory usage', 'all -m shell -a "free -h"'),
        ('system uptime', 'all -m shell -a "uptime"'),
        ('load average', 'all -m shell -a "cat /proc/loadavg"')
    ]
    
    success = True
    for description, command in commands:
        print_colored(f"  Checking {description}...", Colors.YELLOW)
        if not run_ansible_command(command, inventory_file, ansible_dir):
            success = False
    
    return success

def check_services(environment: str, ansible_dir: Path) -> bool:
    """Check critical services"""
    print_colored("🔧 Checking critical services...", Colors.BLUE)
    
    inventory_file = ansible_dir / f"inventories/{environment}.yml"
    
    if not inventory_file.exists():
        print_colored(f"❌ Inventory file not found: {inventory_file}", Colors.RED)
        return False
    
    services = [
        ('SSH service', 'all -m service -a "name=ssh state=started"'),
        ('Docker service', 'all -m service -a "name=docker state=started"'),
    ]
    
    success = True
    for description, command in services:
        print_colored(f"  Checking {description}...", Colors.YELLOW)
        if not run_ansible_command(command, inventory_file, ansible_dir):
            success = False
    
    return success

def check_docker_containers(environment: str, ansible_dir: Path) -> bool:
    """Check Docker containers status"""
    print_colored("🐳 Checking Docker containers...", Colors.BLUE)
    
    inventory_file = ansible_dir / f"inventories/{environment}.yml"
    
    if not inventory_file.exists():
        print_colored(f"❌ Inventory file not found: {inventory_file}", Colors.RED)
        return False
    
    commands = [
        ('container status', 'all -m shell -a "docker ps --format \'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}\'"'),
        ('container health', 'all -m shell -a "docker ps --filter health=healthy --format \'table {{.Names}}\\t{{.Status}}\'"'),
    ]
    
    success = True
    for description, command in commands:
        print_colored(f"  Checking {description}...", Colors.YELLOW)
        if not run_ansible_command(command, inventory_file, ansible_dir):
            success = False
    
    return success

def check_monitoring_endpoints(environment: str, ansible_dir: Path) -> bool:
    """Check monitoring service endpoints"""
    print_colored("📊 Checking monitoring endpoints...", Colors.BLUE)
    
    inventory_file = ansible_dir / f"inventories/{environment}.yml"
    
    if not inventory_file.exists():
        print_colored(f"❌ Inventory file not found: {inventory_file}", Colors.RED)
        return False
    
    # Check if services are responding on their ports
    endpoints = [
        ('Grafana (port 3000)', 'all -m uri -a "url=http://localhost:3000/api/health timeout=10"'),
        ('Prometheus (port 9090)', 'all -m uri -a "url=http://localhost:9090/-/ready timeout=10"'),
        ('Loki (port 3100)', 'all -m uri -a "url=http://localhost:3100/ready timeout=10"'),
    ]
    
    success = True
    for description, command in endpoints:
        print_colored(f"  Checking {description}...", Colors.YELLOW)
        if not run_ansible_command(command, inventory_file, ansible_dir):
            print_colored(f"    ⚠️ {description} may not be responding", Colors.YELLOW)
            # Don't fail the whole check for endpoint issues
    
    return success

def main():
    """Main health check function"""
    parser = argparse.ArgumentParser(description='Infrastructure Health Check Script')
    parser.add_argument('environment', nargs='?', default='dev', 
                       help='Environment to check (default: dev)')
    parser.add_argument('--skip-endpoints', action='store_true',
                       help='Skip monitoring endpoint checks')
    
    args = parser.parse_args()
    
    print_colored(f"🔍 Running health checks for environment: {args.environment}", Colors.BLUE)
    
    # Get project root directory
    project_root = Path(__file__).parent.parent.parent
    ansible_dir = project_root / "ansible"
    
    if not ansible_dir.exists():
        print_colored(f"❌ Ansible directory not found: {ansible_dir}", Colors.RED)
        sys.exit(1)
    
    # Run all health checks
    checks = [
        ("connectivity", check_connectivity),
        ("system resources", check_system_resources),
        ("services", check_services),
        ("docker containers", check_docker_containers),
    ]
    
    if not args.skip_endpoints:
        checks.append(("monitoring endpoints", check_monitoring_endpoints))
    
    failed_checks = []
    
    for check_name, check_function in checks:
        try:
            print_colored(f"\n--- Running {check_name} check ---", Colors.BLUE)
            if not check_function(args.environment, ansible_dir):
                failed_checks.append(check_name)
        except Exception as e:
            print_colored(f"❌ {check_name} check failed with error: {e}", Colors.RED)
            failed_checks.append(check_name)
    
    # Print summary
    print_colored("\n📊 Health Check Summary:", Colors.BLUE)
    
    if not failed_checks:
        print_colored("✅ All health checks passed!", Colors.GREEN)
        sys.exit(0)
    else:
        print_colored(f"❌ {len(failed_checks)} health check(s) failed:", Colors.RED)
        for check in failed_checks:
            print_colored(f"  • {check}", Colors.RED)
        
        print_colored("\n💡 Tips:", Colors.YELLOW)
        print_colored("  • Check server connectivity and SSH access", Colors.YELLOW)
        print_colored("  • Verify services are running: systemctl status <service>", Colors.YELLOW)
        print_colored("  • Check logs: journalctl -u <service> --tail 50", Colors.YELLOW)
        
        sys.exit(1)

if __name__ == "__main__":
    main()
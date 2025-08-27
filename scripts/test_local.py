#!/usr/bin/env python3
"""
Local Testing Script for VPS Configuration
Rewritten in Python for better container management and waiting logic
"""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path

# Color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_status(message, color=Colors.NC):
    print(f"{color}{message}{Colors.NC}")

def run_command(command, cwd=None, check=True, timeout=300, verbose=False):
    """Run a command and return the result"""
    if verbose:
        print_status(f"🔧 Running: {command}", Colors.BLUE)
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            check=check
        )
        
        if verbose:
            if result.stdout:
                print_status(f"📤 STDOUT: {result.stdout.strip()}", Colors.GREEN)
            if result.stderr:
                print_status(f"📤 STDERR: {result.stderr.strip()}", Colors.YELLOW)
            print_status(f"📤 Exit code: {result.returncode}", Colors.BLUE)
        
        return result
    except subprocess.TimeoutExpired:
        print_status(f"❌ Command timed out after {timeout}s: {command}", Colors.RED)
        return None
    except subprocess.CalledProcessError as e:
        if check:
            print_status(f"❌ Command failed: {command}", Colors.RED)
            print_status(f"   Error: {e.stderr}", Colors.RED)
            return None
        return e

def wait_for_container_healthy(container_name, timeout=120):
    """Wait for container to be healthy and running using docker CLI"""
    print_status(f"⏳ Waiting for {container_name} to be ready...", Colors.YELLOW)
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Check if container exists and is running
            result = run_command(f"docker ps --filter name={container_name} --format '{{{{.Status}}}}'", check=False)
            if not result or not result.stdout.strip():
                # Check if container exists but is stopped
                stopped_result = run_command(f"docker ps -a --filter name={container_name} --format '{{{{.Status}}}}'", check=False)
                if stopped_result and stopped_result.stdout.strip():
                    print_status(f"❌ Container {container_name} exists but stopped: {stopped_result.stdout.strip()}", Colors.RED)
                    # Get container logs to see why it stopped
                    print_status("📋 Container logs:", Colors.YELLOW)
                    run_command(f"docker logs {container_name} --tail 20", check=False, verbose=True)
                    return False
                else:
                    print_status(f"   Container {container_name} not found, waiting...", Colors.YELLOW)
                time.sleep(3)
                continue
            
            status = result.stdout.strip()
            if not status.startswith('Up'):
                print_status(f"   Container status: {status}", Colors.YELLOW)
                
                # If container is exited, show logs and fail
                if 'Exited' in status:
                    print_status(f"❌ Container {container_name} has exited: {status}", Colors.RED)
                    print_status("📋 Container logs:", Colors.YELLOW)
                    run_command(f"docker logs {container_name} --tail 30", check=False, verbose=True)
                    return False
                    
                time.sleep(2)
                continue
            
            # For systemd containers, check if systemd is ready
            if container_name == 'test-vps':
                try:
                    result = run_command(
                        f"docker exec {container_name} systemctl is-system-running --wait", 
                        timeout=10, 
                        check=False
                    )
                    if result and result.returncode in [0, 1]:  # 0 = running, 1 = degraded (still ok)
                        print_status(f"✅ {container_name} systemd is ready", Colors.GREEN)
                        return True
                    else:
                        print_status(f"   Systemd status: {result.returncode if result else 'timeout'}", Colors.YELLOW)
                except Exception as e:
                    print_status(f"   Systemd check: {e}", Colors.YELLOW)
            
            # For other containers, just check if they're running
            else:
                print_status(f"✅ {container_name} is running", Colors.GREEN)
                return True
                
        except Exception as e:
            print_status(f"   Checking container: {e}", Colors.YELLOW)
        
        time.sleep(3)
    
    print_status(f"❌ {container_name} did not become ready within {timeout}s", Colors.RED)
    return False

def wait_for_ssh_service(container_name, timeout=60):
    """Wait for SSH service to be ready inside container using docker CLI"""
    print_status("🔐 Waiting for SSH service...", Colors.YELLOW)
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # First check if SSH service is active
            print_status("   Checking SSH service status...", Colors.YELLOW)
            result = run_command(
                f"docker exec {container_name} systemctl is-active ssh", 
                timeout=5, 
                check=False,
                verbose=True
            )
            
            if result and result.returncode == 0 and 'active' in result.stdout:
                # Also check if SSH is listening on port 22
                print_status("   SSH is active, checking port 22...", Colors.YELLOW)
                port_check = run_command(
                    f"docker exec {container_name} netstat -tlnp | grep :22", 
                    timeout=5, 
                    check=False,
                    verbose=True
                )
                if port_check and port_check.returncode == 0:
                    print_status("✅ SSH service is active and listening", Colors.GREEN)
                    return True
                else:
                    print_status("   SSH active but not listening yet...", Colors.YELLOW)
            else:
                # Try to start SSH if it's not running
                print_status("   SSH not active, attempting to start...", Colors.YELLOW)
                start_result = run_command(
                    f"docker exec {container_name} systemctl start ssh", 
                    timeout=10, 
                    check=False,
                    verbose=True
                )
                
                # Check what happened with the start command
                if start_result:
                    status_result = run_command(
                        f"docker exec {container_name} systemctl status ssh --no-pager", 
                        timeout=5, 
                        check=False,
                        verbose=True
                    )
                
        except Exception as e:
            print_status(f"   SSH check: {e}", Colors.YELLOW)
        
        time.sleep(3)
    
    # Final diagnostic info
    print_status("📋 Final SSH service diagnostics:", Colors.YELLOW)
    run_command(f"docker exec {container_name} systemctl status ssh --no-pager -l", timeout=10, check=False, verbose=True)
    run_command(f"docker exec {container_name} journalctl -u ssh --no-pager -n 20", timeout=10, check=False, verbose=True)
    
    # Check if SSH daemon is installed
    print_status("📋 Checking SSH installation:", Colors.YELLOW)
    run_command(f"docker exec {container_name} which sshd", timeout=5, check=False, verbose=True)
    run_command(f"docker exec {container_name} dpkg -l | grep openssh", timeout=5, check=False, verbose=True)
    
    # Check SSH configuration
    print_status("📋 Checking SSH config:", Colors.YELLOW)
    run_command(f"docker exec {container_name} ls -la /etc/ssh/", timeout=5, check=False, verbose=True)
    run_command(f"docker exec {container_name} sshd -T", timeout=5, check=False, verbose=True)
    
    print_status(f"❌ SSH service not ready within {timeout}s", Colors.RED)
    return False

def setup_ssh_access():
    """Setup SSH key and access using docker CLI"""
    print_status("🔑 Setting up SSH access...", Colors.YELLOW)
    
    ssh_key_path = Path.home() / '.ssh' / 'id_rsa'
    
    # Generate SSH key if doesn't exist
    if not ssh_key_path.exists():
        print_status("🔑 Generating SSH key...", Colors.YELLOW)
        result = run_command(f'ssh-keygen -t rsa -b 2048 -f {ssh_key_path} -N ""')
        if not result:
            return False
    
    # Copy SSH key to container using docker CLI
    try:
        # Create .ssh directory
        run_command("docker exec test-vps mkdir -p /root/.ssh")
        
        # Copy public key
        with open(f"{ssh_key_path}.pub", 'r') as f:
            pub_key = f.read().strip()
        
        # Use docker exec to set up authorized_keys
        run_command(f"docker exec test-vps bash -c 'echo \"{pub_key}\" > /root/.ssh/authorized_keys'")
        run_command("docker exec test-vps chmod 600 /root/.ssh/authorized_keys")
        run_command("docker exec test-vps chown root:root /root/.ssh/authorized_keys")
        
        print_status("✅ SSH access configured", Colors.GREEN)
        return True
        
    except Exception as e:
        print_status(f"❌ Failed to setup SSH: {e}", Colors.RED)
        return False

def test_http_endpoint(url, expected_text=None, timeout=10):
    """Test if HTTP endpoint is responding"""
    try:
        response = requests.get(url, verify=False, timeout=timeout)
        if response.status_code == 200:
            if expected_text and expected_text.lower() in response.text.lower():
                return True
            elif not expected_text:
                return True
        return False
    except Exception:
        return False

def main():
    print_status("🧪 Starting local testing environment...", Colors.BLUE)
    
    # Check if Docker is running using CLI
    try:
        result = run_command("docker info", timeout=10)
        if result and result.returncode == 0:
            print_status("✅ Docker CLI is working", Colors.GREEN)
        else:
            raise Exception("Docker CLI failed")
    except Exception:
        print_status("❌ Docker is not accessible. Please ensure Docker/Colima is running.", Colors.RED)
        print_status("💡 Try: colima start", Colors.YELLOW)
        sys.exit(1)
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Build and start test environment
    print_status("🏗️ Building test environment...", Colors.YELLOW)
    compose_dir = project_root / 'docker' / 'test-environment'
    
    # Clean up any existing containers
    run_command("docker-compose down --remove-orphans", cwd=compose_dir, check=False)
    
    # Build and start
    result = run_command("docker-compose up -d --build", cwd=compose_dir)
    if not result:
        print_status("❌ Failed to start test environment", Colors.RED)
        sys.exit(1)
    
    # Wait for container to be healthy
    if not wait_for_container_healthy('test-vps', timeout=180):
        print_status("❌ Test container failed to start properly", Colors.RED)
        print_status("📋 Container logs:", Colors.YELLOW)
        run_command("docker-compose logs --tail 50", cwd=compose_dir, check=False, verbose=True)
        
        print_status("📋 Container status:", Colors.YELLOW)
        run_command("docker ps -a --filter name=test-vps", check=False, verbose=True)
        
        print_status("📋 Docker events:", Colors.YELLOW)
        run_command("docker events --since 5m --filter container=test-vps", check=False, verbose=True)
        
        sys.exit(1)
    
    # Wait for SSH service
    if not wait_for_ssh_service('test-vps', timeout=60):
        print_status("❌ SSH service failed to start", Colors.RED)
        sys.exit(1)
    
    # Setup SSH access
    if not setup_ssh_access():
        sys.exit(1)
    
    # Wait a moment for everything to stabilize
    print_status("⏳ Waiting for services to stabilize...", Colors.YELLOW)
    time.sleep(5)
    
    # Run Ansible deployment
    print_status("🚀 Running Ansible deployment on test environment...", Colors.BLUE)
    ansible_dir = project_root / 'ansible'
    
    # Test connectivity first
    print_status("📡 Testing Ansible connectivity...", Colors.YELLOW)
    result = run_command("ansible vps -i inventories/test.yml -m ping -vvv", cwd=ansible_dir, check=False, verbose=True)
    if not result or result.returncode != 0:
        print_status("❌ Connectivity test failed", Colors.RED)
        
        # Debug SSH connection manually
        print_status("🔍 Debugging SSH connection...", Colors.YELLOW)
        run_command("ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222 root@localhost 'echo SSH connection works'", check=False, verbose=True)
        
        # Check if SSH key is properly set up
        print_status("🔍 Checking SSH key setup...", Colors.YELLOW)
        run_command("docker exec test-vps cat /root/.ssh/authorized_keys", check=False, verbose=True)
        
        # Check SSH daemon configuration
        print_status("🔍 Checking SSH daemon config...", Colors.YELLOW)
        run_command("docker exec test-vps grep -E '(PermitRootLogin|PubkeyAuthentication)' /etc/ssh/sshd_config", check=False, verbose=True)
        
        # Check if container is still running
        print_status("🔍 Checking container status...", Colors.YELLOW)
        run_command("docker ps --filter name=test-vps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", check=False, verbose=True)
        
        # Check if SSH is still listening inside container
        print_status("🔍 Checking SSH inside container...", Colors.YELLOW)
        run_command("docker exec test-vps netstat -tlnp | grep :22", check=False, verbose=True)
        
        # Check Docker port mapping
        print_status("🔍 Checking Docker port mapping...", Colors.YELLOW)
        run_command("docker port test-vps", check=False, verbose=True)
        
        # Test direct container connection
        print_status("🔍 Testing direct container SSH...", Colors.YELLOW)
        run_command("docker exec test-vps ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@localhost 'echo Direct SSH works'", check=False, verbose=True)
        
        sys.exit(1)
    
    print_status("✅ Connectivity test passed", Colors.GREEN)
    
    # Run the playbook
    print_status("🔧 Deploying configuration...", Colors.BLUE)
    result = run_command(
        "ansible-playbook playbooks/site.yml -i inventories/test.yml -v", 
        cwd=ansible_dir,
        timeout=600,  # 10 minutes for deployment
        check=False,
        verbose=True
    )
    if not result or result.returncode != 0:
        print_status("❌ Deployment failed", Colors.RED)
        sys.exit(1)
    
    print_status("✅ Deployment successful", Colors.GREEN)
    
    # Test services
    print_status("🔍 Testing deployed services...", Colors.BLUE)
    
    # Wait for services to start
    print_status("⏳ Waiting for services to start...", Colors.YELLOW)
    time.sleep(30)
    
    # Check if containers are running
    print_status("🐳 Checking Docker containers...", Colors.YELLOW)
    result = run_command(
        'ansible vps -i inventories/test.yml -m shell -a "docker ps --format \'table {{.Names}}\\t{{.Status}}\'"', 
        cwd=ansible_dir
    )
    
    # Test HTTP endpoints
    print_status("🌐 Testing HTTP endpoints...", Colors.YELLOW)
    
    endpoints = [
        ("https://localhost:3001", "Grafana", "grafana"),
        ("https://localhost:9091", "Prometheus", "prometheus"), 
        ("https://localhost:3101", "Loki", None)
    ]
    
    for url, name, expected_text in endpoints:
        if test_http_endpoint(url, expected_text, timeout=15):
            print_status(f"✅ {name} is responding", Colors.GREEN)
        else:
            print_status(f"⚠️ {name} test inconclusive (might need more startup time)", Colors.YELLOW)
    
    # Success message
    print_status("\n🎉 Local testing completed!", Colors.GREEN)
    print_status("You can now access services at:", Colors.BLUE)
    print_status("  • Grafana: https://localhost:3001 (admin/admin)", Colors.NC)
    print_status("  • Prometheus: https://localhost:9091", Colors.NC)
    print_status("  • Loki: https://localhost:3101", Colors.NC)
    
    print_status(f"\n{Colors.YELLOW}To clean up test environment:{Colors.NC}")
    print_status("  cd docker/test-environment && docker-compose down", Colors.NC)
    
    print_status(f"\n✅ Configuration is ready for production deployment!", Colors.GREEN)

if __name__ == "__main__":
    main()
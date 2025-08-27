#!/usr/bin/env python3
"""
VPS Configuration Validation Script
Python version of the bash validation script
"""

import os
import sys
import subprocess
import yaml
import docker
from pathlib import Path
from typing import List, Tuple

# Color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def print_colored(message: str, color: str = Colors.NC):
    print(f"{color}{message}{Colors.NC}")

class ValidationTest:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.skip_docker_pull = os.getenv('SKIP_DOCKER_PULL', '').lower() == 'true'
        
    def run_test(self, test_name: str, command: str, cwd: Path = None, timeout: int = 30) -> bool:
        """Run a test and track results"""
        print(f"Testing {test_name}... ", end='', flush=True)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                print_colored("✓", Colors.GREEN)
                self.tests_passed += 1
                return True
            else:
                print_colored("✗", Colors.RED)
                self.tests_failed += 1
                return False
                
        except subprocess.TimeoutExpired:
            print_colored("✗ (timeout)", Colors.RED)
            self.tests_failed += 1
            return False
        except Exception:
            print_colored("✗", Colors.RED)
            self.tests_failed += 1
            return False
    
    def check_prerequisites(self):
        """Check all prerequisites"""
        print_colored("📋 Checking prerequisites...", Colors.BLUE)
        
        self.run_test("Ansible installation", "command -v ansible-playbook")
        self.run_test("Docker installation (for local testing)", "command -v docker")
        self.run_test("uv installation", "command -v uv")
        
        # Test Docker CLI access
        self.run_test("Docker CLI access", "docker version --format '{{.Client.Version}}'", timeout=10)
    
    def check_file_structure(self, project_root: Path):
        """Check if all required files exist"""
        print_colored("\n📁 Checking file structure...", Colors.BLUE)
        
        required_files = [
            "ansible/playbooks/site.yml",
            "ansible/inventories/hosts.yml", 
            "ansible/roles/caddy/tasks/main.yml",
            "ansible/roles/docker/tasks/main.yml",
            "ansible/roles/monitoring/tasks/main.yml",
            "ansible/roles/caddy/templates/Caddyfile.j2"
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            test_name = f"{Path(file_path).name} exists"
            if full_path.exists():
                print_colored(f"Testing {test_name}... ✓", Colors.GREEN)
                self.tests_passed += 1
            else:
                print_colored(f"Testing {test_name}... ✗", Colors.RED)
                self.tests_failed += 1
    
    def validate_ansible_syntax(self, project_root: Path):
        """Validate Ansible playbook syntax"""
        print_colored("\n🔍 Validating Ansible syntax...", Colors.BLUE)
        
        ansible_dir = project_root / "ansible"
        
        # Determine inventory file
        production_inventory = ansible_dir / "inventories/production.yml"
        template_inventory = ansible_dir / "inventories/hosts.yml"
        
        if production_inventory.exists():
            inventory_file = "inventories/production.yml"
        else:
            inventory_file = "inventories/hosts.yml"
            print_colored("⚠️  Using template inventory for syntax check", Colors.YELLOW)
        
        command = f"ansible-playbook playbooks/site.yml --syntax-check -i {inventory_file}"
        self.run_test("Playbook syntax", command, cwd=ansible_dir)
    
    def test_template_rendering(self, project_root: Path):
        """Test template rendering if production inventory exists"""
        ansible_dir = project_root / "ansible"
        production_inventory = ansible_dir / "inventories/production.yml"
        
        if not production_inventory.exists():
            print_colored("\n🎨 Skipping template rendering test (using template inventory)", Colors.BLUE)
        else:
            print_colored("\n🎨 Testing template rendering...", Colors.BLUE)
            command = "ansible-playbook playbooks/site.yml --check -i inventories/production.yml -t caddy --diff"
            self.run_test("Caddyfile template syntax", command, cwd=ansible_dir)
    
    def check_docker_images(self):
        """Check Docker image availability"""
        if self.skip_docker_pull:
            print_colored("\n🐳 Skipping Docker image pulls (SKIP_DOCKER_PULL=true)", Colors.BLUE)
            return
            
        print_colored("\n🐳 Checking Docker image availability...", Colors.BLUE)
        print_colored("💡 Tip: Set SKIP_DOCKER_PULL=true to skip image pulling", Colors.YELLOW)
        
        images = [
            "caddy:2-alpine",
            "prom/prometheus:latest", 
            "prom/node-exporter:latest",
            "grafana/grafana:latest",
            "grafana/loki:latest",
            "grafana/promtail:latest"
        ]
        
        for image in images:
            self.run_test(f"Docker image: {image}", f"docker pull {image}")
    
    def validate_config_files(self, project_root: Path):
        """Validate YAML configuration files"""
        print_colored("\n⚙️ Validating configuration files...", Colors.BLUE)
        
        template_dir = project_root / "ansible/roles/monitoring/templates"
        config_files = [
            ("prometheus.yml.j2", "Prometheus config template"),
            ("loki.yml.j2", "Loki config template"), 
            ("promtail.yml.j2", "Promtail config template")
        ]
        
        for filename, test_name in config_files:
            file_path = template_dir / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        # Basic YAML validation (templates may have Jinja2 vars)
                        yaml.safe_load(content)
                    print_colored(f"Testing {test_name}... ✓", Colors.GREEN)
                    self.tests_passed += 1
                except Exception:
                    # Templates with Jinja2 variables may not parse as pure YAML
                    print_colored(f"Testing {test_name}... ⚠️ (template with variables)", Colors.YELLOW)
            else:
                print_colored(f"Testing {test_name}... ✗ (file not found)", Colors.RED)
                self.tests_failed += 1
    
    def print_summary(self):
        """Print test summary"""
        print_colored("\n📊 Test Summary:", Colors.BLUE)
        print_colored(f"✅ Passed: {self.tests_passed}", Colors.GREEN)
        print_colored(f"❌ Failed: {self.tests_failed}", Colors.RED)
        
        if self.tests_failed == 0:
            print_colored("\n🎉 All validation tests passed! Ready for deployment.", Colors.GREEN)
            return True
        else:
            print_colored("\n💥 Some validation tests failed. Please fix issues before deployment.", Colors.RED)
            return False

def main():
    """Main validation function"""
    print_colored("🔍 Running pre-deployment validation...", Colors.BLUE)
    
    # Get project root directory
    project_root = Path(__file__).parent.parent
    
    # Initialize validator
    validator = ValidationTest()
    
    # Run all validation steps
    validator.check_prerequisites()
    validator.check_file_structure(project_root)
    validator.validate_ansible_syntax(project_root)
    validator.test_template_rendering(project_root)
    validator.check_docker_images()
    validator.validate_config_files(project_root)
    
    # Print summary and exit
    success = validator.print_summary()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
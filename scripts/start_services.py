#!/usr/bin/env python3
"""
Startup script for LLM Citation Verifier
Manages blockchain setup, private keys, and backend services
"""

import os
import sys
import json
import time
import signal
import subprocess
import platform
from pathlib import Path
from typing import Optional, Dict, Any
from eth_account import Account
from eth_utils import encode_hex

class ServiceManager:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent.absolute()
        self.blockchain_dir = self.base_dir / "blockchain"
        self.backend_dir = self.base_dir / "backend"
        self.rag_dir = self.base_dir / "rag_query"
        self.processes = {}
        self.config_file = self.base_dir / ".env.local"
        self.pk_file = self.base_dir / ".private_key.json"

    def log(self, message: str):
        """Print log message"""
        print(f"{message}")
        print()

    def run_command(self, cmd: list, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, show_output: bool = True) -> subprocess.CompletedProcess:
        """Run command and show output in real-time"""
        cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
        print(f"Running: {cmd_str}")
        print()

        if show_output:
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            output_lines = []
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    output_line = output.strip()
                    output_lines.append(output_line)
                    print(f"    {output_line}")

            return_code = process.poll()
            result = subprocess.CompletedProcess(cmd, return_code, stdout='\n'.join(output_lines))
        else:
            result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)

        return result

    def check_command(self, command: str) -> bool:
        """Check if a command exists in PATH"""
        try:
            subprocess.run([command, "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def ensure_dependencies(self) -> bool:
        """Check that required dependencies are available"""
        print("Checking dependencies...")
        print()

        # Check for Python - Windows uses 'python', Unix uses 'python3'
        python_cmd = "python" if platform.system() == "Windows" else "python3"
        if not self.check_command(python_cmd):
            # Try the alternative if first fails
            alt_python_cmd = "python3" if platform.system() == "Windows" else "python"
            if not self.check_command(alt_python_cmd):
                print("ERROR: Python 3 is required but not found")
                print("Please install Python 3 and dependencies first:")
                print("  pip install -r scripts/startup_requirements.txt")
                print("  pip install -r scripts/backend_requirements.txt")
                print()
                return False


        if not self.check_command("forge"):
            print("ERROR: Foundry not found")
            print("Please install Foundry first:")
            print("  Visit: https://getfoundry.sh/")
            print()
            return False

        print("All dependencies available")
        print()
        return True

    def manage_private_key(self) -> Dict[str, Any]:
        """Use Anvil's first test account as admin account"""
        anvil_private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        anvil_address = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

        pk_data = {
            "private_key": anvil_private_key,
            "address": anvil_address,
            "created_at": time.time()
        }

        # Save for reference
        with open(self.pk_file, 'w') as f:
            json.dump(pk_data, f, indent=2)

        print(f"Using Anvil test account: {anvil_address}")
        print(f"Private key saved to: {self.pk_file}")
        print()
        return pk_data

    def setup_blockchain(self) -> bool:
        """Initialize blockchain project"""
        print("Setting up blockchain environment...")
        print()

        if not self.blockchain_dir.exists():
            print("ERROR: blockchain directory not found")
            print()
            return False

        os.chdir(self.blockchain_dir)

        if not (self.blockchain_dir / "foundry.toml").exists():
            print("Initializing Foundry project...")
            cmd = ["forge", "init", "--force"]
            result = self.run_command(cmd, cwd=self.blockchain_dir)
            if result.returncode != 0:
                print("Failed to initialize Foundry project")
                return False
            print()
        else:
            print("Foundry project already initialized")
            print()

        print("Installing OpenZeppelin contracts...")
        cmd = ["forge", "install", "OpenZeppelin/openzeppelin-contracts"]
        result = self.run_command(cmd, cwd=self.blockchain_dir)
        if result.returncode != 0:
            print("Warning: Failed to install OpenZeppelin contracts")
        print()

        contract_path = self.blockchain_dir / "src" / "CitationRegistry.sol"
        if not contract_path.exists():
            print("ERROR: CitationRegistry.sol not found in blockchain/src/")
            print("Please ensure the smart contract file is present")
            print()
            return False

        print("Blockchain setup completed")
        print()
        return True

    def start_anvil(self) -> bool:
        """Start local Ethereum node with Anvil"""
        print("Starting Anvil local Ethereum node...")
        print()

        os.chdir(self.blockchain_dir)

        try:
            print("Running: anvil --host 127.0.0.1 --port 8545")
            process = subprocess.Popen(
                ["anvil", "--host", "127.0.0.1", "--port", "8545"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Wait a bit and check if process is still running
            time.sleep(5)
            if process.poll() is not None:
                stdout, _ = process.communicate()
                print(f"Anvil process died: {stdout}")
                print()
                return False

            self.processes["anvil"] = process
            print("Anvil started successfully on http://127.0.0.1:8545")
            print()
            return True

        except FileNotFoundError:
            print("ERROR: anvil command not found. Please ensure Foundry is installed correctly")
            print()
            return False
        except Exception as e:
            print(f"Error starting Anvil: {e}")
            print()
            return False

    def deploy_contract(self, pk_data: Dict[str, Any]) -> Optional[str]:
        """Deploy the smart contract and return contract address"""
        print("\n" + "="*70)
        self.log("DEPLOYING CITATION REGISTRY CONTRACT")
        print("="*70)

        os.chdir(self.blockchain_dir)

        try:
            print("Getting contract bytecode...")
            print()
            cmd = ["forge", "inspect", "CitationRegistry", "bytecode"]
            result = self.run_command(cmd, cwd=self.blockchain_dir)
            if result.returncode != 0:
                print("Failed to get contract bytecode")
                print()
                return None

            bytecode = result.stdout.strip() if result.stdout else ""
            if not bytecode:
                print("ERROR: Contract bytecode is empty")
                print()
                return None

            print()
            admin_address = pk_data["address"]
            print(f"Encoding constructor args for address: {admin_address}")
            print()

            # Encode constructor arguments directly in Python instead of using shell command
            try:
                # Remove 0x prefix if present and convert to bytes
                addr_hex = admin_address.replace('0x', '')
                addr_bytes = bytes.fromhex(addr_hex)
                # Pad to 20 bytes (Ethereum address size)
                addr_bytes = addr_bytes.rjust(20, b'\0')
                # Encode as constructor argument (32-byte slot)
                encoded_args = encode_hex(addr_bytes.rjust(32, b'\0'))
                print(f"Encoded constructor args: {encoded_args}")
            except Exception as e:
                print(f"Failed to encode constructor args: {e}")
                print()
                return None

            print()
            print(f"Deploying contract with admin: {admin_address}")
            deploy_cmd = [
                "cast", "send",
                "--rpc-url", "http://127.0.0.1:8545",
                "--private-key", pk_data["private_key"],
                "--create", bytecode,
                encoded_args
            ]

            print()
            result = subprocess.run(deploy_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print("Failed to deploy contract:")
                print(f"    STDOUT: {result.stdout}")
                print(f"    STDERR: {result.stderr}")
                print()
                return None

            output = result.stdout
            print("Deployment output:")
            print(f"    {output}")
            print()

            import re
            # Extract transaction hash from deployment output for robust address extraction
            tx_hash_match = re.search(r'transactionHash\s+(0x[a-fA-F0-9]{64})', output, re.IGNORECASE)
            if tx_hash_match:
                tx_hash = tx_hash_match.group(1)
                print(f"Transaction hash: {tx_hash}")
                print("Getting transaction receipt...")
                
                # Get structured receipt using transaction hash
                receipt_cmd = ["cast", "receipt", tx_hash, "--json", "--rpc-url", "http://127.0.0.1:8545"]
                receipt_result = subprocess.run(receipt_cmd, capture_output=True, text=True)
                
                if receipt_result.returncode == 0:
                    try:
                        receipt = json.loads(receipt_result.stdout)
                        contract_address = receipt.get("contractAddress")
                        
                        if contract_address:
                            print(f"Contract deployed at: {contract_address}")
                            
                            # Verify contract was actually deployed by checking code size
                            verify_cmd = ["cast", "codesize", contract_address, "--rpc-url", "http://127.0.0.1:8545"]
                            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)

                            if verify_result.returncode == 0 and verify_result.stdout.strip() != "0":
                                print(f"Contract code size: {verify_result.stdout.strip()} bytes - Deployment verified")
                                print()
                                self.save_config({"CONTRACT_ADDRESS": contract_address})
                                return contract_address
                            else:
                                print("ERROR: Contract deployment failed - no code found at address")
                                print(f"    Verification stdout: {verify_result.stdout}")
                                print(f"    Verification stderr: {verify_result.stderr}")
                                print()
                                return None
                        else:
                            print("ERROR: No contract address found in transaction receipt")
                            print()
                            return None
                            
                    except json.JSONDecodeError as e:
                        print(f"ERROR: Failed to parse transaction receipt JSON: {e}")
                        print(f"    Receipt output: {receipt_result.stdout}")
                        print()
                        return None
                else:
                    print(f"ERROR: Failed to get transaction receipt: {receipt_result.stderr}")
                    print()
                    return None
            else:
                print("Could not extract transaction hash from deployment output")
                print("Attempting fallback regex extraction...")
                # Fallback to regex method
                address_match = re.search(r'contractAddress\s+(0x[a-fA-F0-9]{40})', output, re.IGNORECASE)
                if address_match:
                    contract_address = address_match.group(1)
                    print(f"Contract deployed at (fallback): {contract_address}")
                    
                    # Verify contract was actually deployed by checking code size
                    verify_cmd = ["cast", "codesize", contract_address, "--rpc-url", "http://127.0.0.1:8545"]
                    verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)

                    if verify_result.returncode == 0 and verify_result.stdout.strip() != "0":
                        print(f"Contract code size: {verify_result.stdout.strip()} bytes - Deployment verified")
                        print()
                        self.save_config({"CONTRACT_ADDRESS": contract_address})
                        return contract_address
                    else:
                        print("ERROR: Contract deployment failed - no code found at address")
                        print()
                        return None
                else:
                    print("Could not extract contract address from deployment output")
                    print()
                    return None

        except Exception as e:
            print(f"Error deploying contract: {e}")
            print()
            return None

    def save_config(self, config: Dict[str, str]):
        """Save configuration to .env.local file"""
        with open(self.config_file, 'w') as f:
            for key, value in config.items():
                f.write(f"{key}={value}\n")
        print(f"Configuration saved to {self.config_file}")
        print()

    def start_backend(self, pk_data: Dict[str, Any]) -> bool:
        """Start the backend API server"""
        print("\n" + "="*70)
        self.log("STARTING BACKEND API SERVER")
        print("="*70)

        os.chdir(self.backend_dir)

        try:
            env = os.environ.copy()
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and '=' in line:
                            key, value = line.split('=', 1)
                            env[key] = value

            # Set the private key for backend to use
            env["ETH_PRIVATE_KEY"] = pk_data["private_key"]

            print()
            print("Starting backend server...")
            python_name = os.path.basename(sys.executable)
            print(f"Running: {python_name} run_backend.py")
            print()
            process = subprocess.Popen(
                [sys.executable, "run_backend.py"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.processes["backend"] = process
            print("Backend API started on http://127.0.0.1:8000")
            print()
            return True

        except Exception as e:
            print(f"Error starting backend: {e}")
            print()
            return False

    def load_papers_to_backend(self, pk_data: Dict[str, Any]) -> bool:
        """Load all papers from rag_query/paper.json into the backend"""
        print("\n" + "="*70)
        print("LOADING PAPERS INTO BACKEND")
        print("="*70)
        print()

        paper_file = self.rag_dir / "paper.json"
        if not paper_file.exists():
            print("No paper.json found in rag_query/")
            print()
            return True

        try:
            with open(paper_file, 'r') as f:
                papers = json.load(f)

            print(f"Found {len(papers)} papers in paper.json")
            print()

            print("Waiting for backend to be ready...")
            print()

            # Check if backend is actually responding
            for i in range(15):
                try:
                    import requests
                    response = requests.get("http://127.0.0.1:8000/health", timeout=5)
                    if response.status_code == 200:
                        print("Backend is responding")
                        print()
                        break
                except:
                    print(f"Backend not ready yet, waiting... ({i+1}/15)")
                    time.sleep(2)
            else:
                print("ERROR: Backend failed to start responding")
                print()
                return False

            success_count = 0
            for i, paper in enumerate(papers, 1):
                # Validate required fields first
                if not paper.get('title'):
                    print(f"Skipping paper {i}/{len(papers)}: Missing title")
                    continue
                    
                if not paper.get('doi'):
                    print(f"Skipping paper {i}/{len(papers)}: '{paper['title'][:50]}...' - Missing DOI")
                    continue
                
                print(f"Registering paper {i}/{len(papers)}: {paper['title'][:50]}...")

                # Generate proper signature for authentication
                message = f"Register paper: {paper['doi']}"
                try:
                    from eth_account.messages import encode_defunct

                    # Sign the message with the admin private key
                    encoded_message = encode_defunct(text=message)
                    signed_message = Account.from_key(pk_data["private_key"]).sign_message(encoded_message)
                    signature = signed_message.signature.hex()

                except Exception as e:
                    print(f"    Failed to generate signature for {paper['doi']}: {e}")
                    continue

                paper_data = {
                    "auth": {
                        "signature": signature,
                        "message": message
                    },
                    "metadata": {
                        "doi": paper["doi"],
                        "title": paper["title"],
                        "authors": paper.get("authors", "").split(", ") if isinstance(paper.get("authors"), str) else [],
                        "date": paper.get("date", ""),
                        "abstract": paper.get("abstract", ""),
                        "journal": paper.get("journal", "")
                    },
                    "full_text": None,
                    "chunk_size": 1024
                }

                try:
                    import requests
                    response = requests.post(
                        "http://127.0.0.1:8000/register",
                        json=paper_data,
                        timeout=30
                    )

                    if response.status_code == 200:
                        success_count += 1
                        print(f"    Successfully registered: {paper['doi']}")
                    else:
                        print(f"    Failed to register {paper['doi']}: {response.status_code}")
                        if response.status_code != 404:
                            print(f"       Response: {response.text}")

                except requests.exceptions.RequestException as e:
                    print(f"    Request failed for {paper['doi']}: {e}")
                    continue
                except Exception as e:
                    print(f"    Error processing {paper['doi']}: {e}")
                    continue

            print(f"Paper loading completed: {success_count}/{len(papers)} papers successfully registered")
            print()
            return True

        except json.JSONDecodeError as e:
            print(f"Failed to parse paper.json: {e}")
            print()
            return False
        except Exception as e:
            print(f"Error loading papers: {e}")
            print()
            return False

    def cleanup(self):
        """Clean up all processes"""
        if hasattr(self, '_cleanup_in_progress'):
            return  # Prevent multiple cleanup calls
        self._cleanup_in_progress = True
        
        print("Shutting down services...")
        for name, process in list(self.processes.items()):
            if process.poll() is None:
                print(f"Stopping {name}...")
                try:
                    process.terminate()
                    process.wait(timeout=3)
                    print(f"  {name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    print(f"  Force killing {name}...")
                    process.kill()
                    try:
                        process.wait(timeout=2)
                        print(f"  {name} force killed")
                    except subprocess.TimeoutExpired:
                        print(f"  Warning: {name} may still be running")
                except Exception as e:
                    print(f"  Error stopping {name}: {e}")
            else:
                print(f"  {name} already stopped")
        
        self.processes.clear()
        print("Cleanup completed")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        if hasattr(self, '_shutdown_in_progress'):
            print("\nForce exit...")
            os._exit(1)
        
        self._shutdown_in_progress = True
        print("\nReceived shutdown signal...")
        print()
        self.cleanup()
        sys.exit(0)

    def run(self):
        """Main startup sequence"""
        print("="*70)
        print("Starting LLM Citation Verifier (Blockchain + Backend)...")
        print("="*70)
        print()

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        try:
            if not self.ensure_dependencies():
                return False

            pk_data = self.manage_private_key()
            if not pk_data:
                return False

            if not self.setup_blockchain():
                return False

            if not self.start_anvil():
                return False

            print("Waiting for Anvil to be fully ready...")
            print()

            # Check if Anvil is actually responding
            for i in range(10):
                try:
                    import requests
                    response = requests.post("http://127.0.0.1:8545", json={"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}, timeout=5)
                    if response.status_code == 200:
                        print("Anvil is responding")
                        print()
                        break
                except:
                    print(f"Anvil not ready yet, waiting... ({i+1}/10)")
                    time.sleep(2)
            else:
                print("ERROR: Anvil failed to start responding")
                print()
                return False

            contract_address = self.deploy_contract(pk_data)
            if not contract_address:
                print("ERROR: Contract deployment failed. Exiting.")
                print()
                return False

            if not self.start_backend(pk_data):
                print("ERROR: Backend startup failed. Exiting.")
                print()
                return False

            if not self.load_papers_to_backend(pk_data):
                print("ERROR: Paper loading failed. Exiting.")
                print()
                return False

            print("\n" + "="*60)
            print("SERVICES STARTED SUCCESSFULLY!")
            print("="*60)
            print(f"Admin Address: {pk_data['address']}")
            if contract_address:
                print(f"Contract Address: {contract_address}")
            print("Anvil (Ethereum Node): http://127.0.0.1:8545")
            print("Backend API: http://127.0.0.1:8000")
            print("Backend Health Check: http://127.0.0.1:8000/health")
            print("Papers loaded from rag_query/paper.json")
            print("Backend API running on port 8000")
            print("\nPress Ctrl+C to stop all services")
            print("="*60)

            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error during startup: {e}")
            print()
            return False
        finally:
            self.cleanup()

        return True

if __name__ == "__main__":
    manager = ServiceManager()
    success = manager.run()
    sys.exit(0 if success else 1)

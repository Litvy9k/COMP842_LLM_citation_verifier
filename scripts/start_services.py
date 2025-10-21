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

        # Check for Node.js and npm (required for Hardhat)
        if not self.check_command("node"):
            print("ERROR: Node.js not found")
            print("Please install Node.js first:")
            print("  Visit: https://nodejs.org/")
            print()
            return False

        if not self.check_command("npm"):
            print("ERROR: npm not found")
            print("Please install npm (comes with Node.js)")
            print()
            return False

        # Check for Hardhat
        if not self.check_command("npx"):
            print("ERROR: npx not found")
            print("Please ensure Node.js is installed correctly")
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

        # Check if package.json exists, if not initialize Hardhat project
        if not (self.blockchain_dir / "package.json").exists():
            print("Initializing Hardhat project...")
            cmd = ["npm", "init", "-y"]
            result = self.run_command(cmd, cwd=self.blockchain_dir)
            if result.returncode != 0:
                print("Failed to initialize npm project")
                return False

            # Install Hardhat and dependencies
            print("Installing Hardhat and dependencies...")
            install_cmd = [
                "npm", "install", "--save-dev",
                "hardhat@^2.19.0",
                "@nomicfoundation/hardhat-toolbox@^4.0.0"
            ]
            result = self.run_command(install_cmd, cwd=self.blockchain_dir)
            if result.returncode != 0:
                print("Failed to install Hardhat dependencies")
                return False

            # Install OpenZeppelin contracts
            print("Installing OpenZeppelin contracts...")
            oz_cmd = ["npm", "install", "@openzeppelin/contracts@^5.0.0"]
            result = self.run_command(oz_cmd, cwd=self.blockchain_dir)
            if result.returncode != 0:
                print("Warning: Failed to install OpenZeppelin contracts")
            print()
        else:
            print("Hardhat project already initialized")
            print()

        # Ensure contracts directory exists
        contracts_dir = self.blockchain_dir / "contracts"
        if not contracts_dir.exists():
            contracts_dir.mkdir(exist_ok=True)
            print("Created contracts directory")

        # Check if CitationRegistry.sol exists in contracts folder
        contract_path = contracts_dir / "CitationRegistry.sol"
        src_contract_path = self.blockchain_dir / "src" / "CitationRegistry.sol"

        if src_contract_path.exists() and not contract_path.exists():
            # Move contract from src to contracts
            import shutil
            shutil.move(str(src_contract_path), str(contract_path))
            print(f"Moved CitationRegistry.sol from src/ to contracts/")
        elif not contract_path.exists():
            print("ERROR: CitationRegistry.sol not found")
            print("Please ensure the smart contract file is present")
            print()
            return False

        print("Blockchain setup completed")
        print()
        return True

    def start_hardhat_node(self) -> bool:
        """Start local Ethereum node with Hardhat"""
        print("Starting Hardhat local Ethereum node...")
        print()

        os.chdir(self.blockchain_dir)

        try:
            print("Running: npx hardhat node")
            process = subprocess.Popen(
                ["npx", "hardhat", "node"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Wait a bit and check if process is still running
            time.sleep(5)
            if process.poll() is not None:
                stdout, _ = process.communicate()
                print(f"Hardhat node process died: {stdout}")
                print()
                return False

            self.processes["hardhat"] = process
            print("Hardhat node started successfully on http://127.0.0.1:8545")
            print()
            return True

        except FileNotFoundError:
            print("ERROR: npx hardhat node command not found. Please ensure Hardhat is installed correctly")
            print()
            return False
        except Exception as e:
            print(f"Error starting Hardhat node: {e}")
            print()
            return False

    def deploy_contract(self, pk_data: Dict[str, Any]) -> Optional[str]:
        """Deploy the smart contract and return contract address"""
        print("\n" + "="*70)
        self.log("DEPLOYING CITATION REGISTRY CONTRACT")
        print("="*70)

        os.chdir(self.blockchain_dir)

        try:
            # Set environment variables for deployment script
            env = os.environ.copy()
            env["INITIAL_REGISTRAR"] = pk_data["address"]

            print("Compiling contracts...")
            compile_cmd = ["npx", "hardhat", "compile"]
            result = self.run_command(compile_cmd, cwd=self.blockchain_dir, env=env)
            if result.returncode != 0:
                print("Failed to compile contracts")
                print()
                return None

            print("Deploying contract...")
            deploy_cmd = ["npx", "hardhat", "run", "scripts/deploy.js", "--network", "localhost"]
            result = self.run_command(deploy_cmd, cwd=self.blockchain_dir, env=env)
            if result.returncode != 0:
                print("Failed to deploy contract")
                print()
                return None

            # Read deployment info from the deployment.json file created by the deploy script
            deployment_file = self.blockchain_dir / "deployment.json"
            if deployment_file.exists():
                with open(deployment_file, 'r') as f:
                    deployment_info = json.load(f)

                contract_address = deployment_info.get("contractAddress")
                if contract_address:
                    print(f"Contract deployed at: {contract_address}")

                    # Verify contract was actually deployed by checking code size
                    verify_cmd = ["cast", "codesize", contract_address, "--rpc-url", "http://127.0.0.1:8545"]
                    try:
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
                    except FileNotFoundError:
                        # If cast is not available, trust the deployment script
                        print("Contract deployment verification skipped (cast not available)")
                        print()
                        self.save_config({"CONTRACT_ADDRESS": contract_address})
                        return contract_address
                else:
                    print("ERROR: No contract address found in deployment info")
                    print()
                    return None
            else:
                print("ERROR: Deployment info file not found")
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
            # Make sure contract address is available in environment
            if not env.get("CONTRACT_ADDRESS"):
                if self.config_file.exists():
                    with open(self.config_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('CONTRACT_ADDRESS='):
                                env["CONTRACT_ADDRESS"] = line.split('=', 1)[1]
                                break

            # Set correct ABI path for contract
            abi_path = self.blockchain_dir / "artifacts" / "contracts" / "CitationRegistry.sol" / "CitationRegistry.json"
            if abi_path.exists():
                env["CONTRACT_ABI_PATH"] = str(abi_path)

            print()
            print("Starting backend server...")
            python_name = os.path.basename(sys.executable)
            print(f"Running: {python_name} run_backend.py")
            print()
            process = subprocess.Popen(
                [sys.executable, "run_backend.py"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
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
                    response = requests.get("http://127.0.0.1:8000/", timeout=5)
                    if response.status_code == 200 and response.json().get("ok"):
                        print("Backend is responding")
                        print()
                        break
                except:
                    print(f"Backend not ready yet, waiting... ({i+1}/15)")
                    time.sleep(2)
            else:
                print("ERROR: Backend failed to start responding")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    return False

            success_count = 0
            processed_dois = set()

            for i, paper in enumerate(papers, 1):

                # Validate required fields first
                if not paper.get('title'):
                    continue

                if not paper.get('doi'):
                    continue

                # Skip duplicate DOIs
                if paper['doi'] in processed_dois:
                    continue

                processed_dois.add(paper['doi'])

                print(f"Registering paper: {paper['title'][:50]}...")

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
                        timeout=5
                    )

                    if response.status_code == 200:
                        success_count += 1
                        print(f"    Successfully registered: {paper['doi']}")
                    else:
                        print(f"    Failed to register {paper['doi']}: {response.status_code}")
                        if response.status_code != 404:
                            print(f"       Response: {response.text}")

                except requests.exceptions.Timeout:
                    print(f"    Request timed out for {paper['doi']}")
                    continue
                except requests.exceptions.RequestException as e:
                    print(f"    Request failed for {paper['doi']}: {e}")
                    continue
                except Exception as e:
                    print(f"    Error processing {paper['doi']}: {e}")
                    continue

            print(f"Added {success_count} papers")
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

            if not self.start_hardhat_node():
                return False

            print("Waiting for Hardhat node to be fully ready...")
            print()

            # Check if Hardhat node is actually responding
            for i in range(10):
                try:
                    import requests
                    response = requests.post("http://127.0.0.1:8545", json={"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}, timeout=5)
                    if response.status_code == 200:
                        print("Hardhat node is responding")
                        print()
                        break
                except:
                    print(f"Hardhat node not ready yet, waiting... ({i+1}/10)")
                    time.sleep(2)
            else:
                print("ERROR: Hardhat node failed to start responding")
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
            print("Hardhat Node (Ethereum): http://127.0.0.1:8545")
            print("Backend API: http://127.0.0.1:8000")
            print("Backend Health Check: http://127.0.0.1:8000/")
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

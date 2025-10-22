const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Starting deployment...");

  // Get deployer account (first account from hardhat node)
  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);

  // Get initial registrar address from environment or use deployer
  const initialRegistrar = process.env.INITIAL_REGISTRAR || deployer.address;
  console.log("Initial registrar address:", initialRegistrar);

  // Get contract bytecode to verify compilation
  const CitationRegistry = await ethers.getContractFactory("CitationRegistry");
  console.log("Compiling contract...");

  // Deploy contract
  console.log("Deploying CitationRegistry...");
  const citationRegistry = await CitationRegistry.deploy(initialRegistrar);

  // Wait for deployment to complete
  await citationRegistry.waitForDeployment();

  const contractAddress = await citationRegistry.getAddress();
  console.log("CitationRegistry deployed to:", contractAddress);

  // Verify contract was deployed by checking code size
  const codeSize = await ethers.provider.getCode(contractAddress);
  if (codeSize === "0x") {
    throw new Error("Contract deployment failed - no code found at address");
  }

  console.log("Contract code size:", codeSize.length / 2 - 2, "bytes");
  console.log("Deployment verified successfully");

  // Grant REGISTRAR_ROLE to additional test accounts for web testing
  console.log("\nGranting REGISTRAR_ROLE to test accounts...");
  const signers = await ethers.getSigners();

  // Grant REGISTRAR_ROLE to account 1 (0x70997970C51812dc3A010C7d01b50e0d17dc79C8) for web testing
  if (signers.length > 1) {
    const testAccount = signers[1];
    console.log("Granting REGISTRAR_ROLE to test account:", testAccount.address);

    const grantTx = await citationRegistry.grantRegistrarRole(testAccount.address);
    await grantTx.wait();

    console.log("REGISTRAR_ROLE granted to test account successfully");
  } else {
    console.log("Warning: Only one signer available, test account not configured");
  }

  // Save deployment info for the Python script
  const deploymentInfo = {
    contractAddress: contractAddress,
    deployerAddress: deployer.address,
    initialRegistrar: initialRegistrar,
    testRegistrarAddress: signers.length > 1 ? signers[1].address : null,
    deploymentHash: citationRegistry.deploymentTransaction().hash,
    network: "localhost",
    timestamp: new Date().toISOString()
  };

  // Save deployment info to file for Python script to read
  const deploymentFile = path.join(__dirname, "../deployment.json");
  fs.writeFileSync(deploymentFile, JSON.stringify(deploymentInfo, null, 2));
  console.log("Deployment info saved to:", deploymentFile);

  // Also save to .env.local format for compatibility with existing Python script
  const envFile = path.join(__dirname, "../../.env.local");
  fs.writeFileSync(envFile, `CONTRACT_ADDRESS=${contractAddress}\n`);
  console.log("Contract address saved to .env.local");

  console.log("\n" + "=".repeat(60));
  console.log("DEPLOYMENT COMPLETED SUCCESSFULLY");
  console.log("=".repeat(60));
  console.log("Contract Address:", contractAddress);
  console.log("Deployer Address:", deployer.address);
  console.log("Initial Registrar:", initialRegistrar);
  if (signers.length > 1) {
    console.log("Test Registrar (Account 1):", signers[1].address);
  }
  console.log("Network: http://127.0.0.1:8545");

  return deploymentInfo;
}

// Execute deployment
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("Deployment failed:", error);
    process.exit(1);
  });
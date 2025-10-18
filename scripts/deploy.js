// Deploy script for AgentVerifier contract
const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("Starting deployment of AgentVerifier contract...\n");

  // Get the contract factory
  const AgentVerifier = await hre.ethers.getContractFactory("AgentVerifier");
  
  console.log("Deploying AgentVerifier...");
  
  // Deploy the contract
  const agentVerifier = await AgentVerifier.deploy();
  
  // Wait for deployment to complete
  await agentVerifier.waitForDeployment();
  
  // Get the deployed contract address
  const contractAddress = await agentVerifier.getAddress();
  
  console.log("\n✓ AgentVerifier deployed successfully!");
  console.log("Contract address:", contractAddress);
  
  // Save deployment information to artifacts directory
  const deploymentInfo = {
    contractName: "AgentVerifier",
    address: contractAddress,
    network: hre.network.name,
    deploymentTime: new Date().toISOString(),
    deployer: (await hre.ethers.getSigners())[0].address
  };
  
  // Create artifacts directory if it doesn't exist
  const artifactsDir = path.join(__dirname, "..", "artifacts");
  const deploymentsDir = path.join(artifactsDir, "deployments");
  
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }
  
  // Save deployment info
  const deploymentPath = path.join(deploymentsDir, "AgentVerifier.json");
  fs.writeFileSync(
    deploymentPath,
    JSON.stringify(deploymentInfo, null, 2)
  );
  
  console.log("\n✓ Deployment info saved to:", deploymentPath);
  console.log("\nDeployment details:");
  console.log("  - Network:", hre.network.name);
  console.log("  - Deployer:", deploymentInfo.deployer);
  console.log("  - Timestamp:", deploymentInfo.deploymentTime);
  
  // Get and display the contract ABI location
  const artifactPath = path.join(
    artifactsDir,
    "contracts",
    "AgentVerifier.sol",
    "AgentVerifier.json"
  );
  
  console.log("\n✓ Contract ABI available at:", artifactPath);
  console.log("\nContract is ready for backend integration!");
}

// Execute the deployment
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("\n✗ Deployment failed:");
    console.error(error);
    process.exit(1);
  });


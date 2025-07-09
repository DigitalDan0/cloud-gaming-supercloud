#!/bin/bash
set -e

echo "Setting up Cloud Gaming development environment..."

# Update package lists
sudo apt-get update

# Install Akash CLI
echo "Installing Akash CLI..."
curl -sSfL https://raw.githubusercontent.com/akash-network/provider/main/install.sh | sh
sudo mv ./bin/akash /usr/local/bin/

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install fastapi uvicorn pytest pytest-mock stripe python-multipart

# Install development tools
pip install black pylint pytest-cov

# Set up git hooks (if needed)
if [ -d ".git" ]; then
    echo "Setting up git hooks..."
    git config --global init.defaultBranch main
    git config --global user.email "dev@cloudgaming.ai"
    git config --global user.name "Cloud Gaming Dev"
fi

# Create test directories
mkdir -p /tmp/test-data

# Set up environment variables for development
echo "export AKASH_NODE=https://rpc.akash.forbole.com:443" >> ~/.bashrc
echo "export AKASH_CHAIN_ID=akashnet-2" >> ~/.bashrc
echo "export AKASH_KEYRING_BACKEND=test" >> ~/.bashrc
echo "export STRIPE_SECRET_KEY=sk_test_placeholder" >> ~/.bashrc

# Make scripts executable
chmod +x images/ubuntu-sunshine/entrypoint.sh

echo "Development environment setup complete!"
echo "Run 'akash version' to verify Akash CLI installation"
echo "Run 'cd broker && python -m uvicorn main:app --reload' to start the broker"
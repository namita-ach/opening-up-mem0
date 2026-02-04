#!/bin/bash

# Mem0 LOCOMO Benchmark - One-Time Setup Script
# Run this once to set up your environment

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Mem0 LOCOMO Benchmark - Setup Wizard            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}\n"

# Step 1: Check Python
echo -e "${BLUE}[1/5] Checking Python installation...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "   ✅ $PYTHON_VERSION"
else
    echo -e "   ${RED}❌ Python 3 not found${NC}"
    exit 1
fi

# Step 2: Install dependencies
echo -e "\n${BLUE}[2/5] Installing Python dependencies...${NC}"
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
    echo -e "   ✅ Dependencies installed"
else
    echo -e "   ${YELLOW}⚠️  requirements.txt not found, installing manually...${NC}"
    pip install mem0ai openai python-dotenv jinja2 nltk tqdm numpy scikit-learn pandas bert-score rouge-score sentence-transformers
fi

# Step 3: Download NLTK data
echo -e "\n${BLUE}[3/5] Downloading NLTK data...${NC}"
python3 -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('wordnet', quiet=True); print('   ✅ NLTK data downloaded')"

# Step 4: Create .env file
echo -e "\n${BLUE}[4/5] Setting up environment configuration...${NC}"
if [ ! -f .env ]; then
    echo -e "   📝 Creating .env file from template..."
    cp .env.example .env
    echo -e "   ${YELLOW}⚠️  IMPORTANT: You need to edit .env with your API keys${NC}"
    echo -e "\n   Required API keys:"
    echo -e "   • OPENAI_API_KEY"
    echo -e "   • MEM0_API_KEY"
    echo -e "   • MEM0_PROJECT_ID"
    echo -e "   • MEM0_ORGANIZATION_ID"
    echo -e "\n   ${GREEN}Edit with: nano .env${NC}"
else
    echo -e "   ✅ .env file already exists"
fi

# Step 5: Create results directory
echo -e "\n${BLUE}[5/5] Setting up results directory...${NC}"
mkdir -p results
echo -e "   ✅ results/ directory created"

# Verify setup
echo -e "\n${BLUE}Running setup verification...${NC}\n"
python3 verify_setup.py

echo -e "\n${GREEN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Setup Complete!                                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}\n"

echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Edit .env file with your API keys:"
echo -e "   ${GREEN}nano .env${NC}"
echo -e ""
echo -e "2. Verify setup again:"
echo -e "   ${GREEN}python3 verify_setup.py${NC}"
echo -e ""
echo -e "3. Run your first benchmark:"
echo -e "   ${GREEN}./run_mem0_benchmark.sh quick${NC}"
echo -e ""
echo -e "For help: ${GREEN}./run_mem0_benchmark.sh help${NC}\n"

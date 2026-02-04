#!/bin/bash

# Zep LOCOMO Benchmark Runner
# This script runs benchmarking with Zep on the LOCOMO dataset
# and evaluates with F1, BLEU, LLM Score, and Latency metrics

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Zep LOCOMO Benchmark Runner ===${NC}\n"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo -e "Please copy .env.example to .env and fill in your API keys:"
    echo -e "  ${YELLOW}cp .env.example .env${NC}"
    exit 1
fi

# Check for required Python packages
echo -e "${BLUE}Checking dependencies...${NC}"
python3 -c "import zep_cloud, openai, nltk, jinja2, tqdm" 2>/dev/null || {
    echo -e "${YELLOW}Some dependencies are missing. Installing...${NC}"
    pip install zep-cloud openai python-dotenv jinja2 nltk tqdm numpy scikit-learn pandas
}

# Create results directory if it doesn't exist
mkdir -p results

# Function to run zep add (store memories)
run_zep_add() {
    echo -e "\n${GREEN}[1/3] Adding memories to Zep...${NC}"
    python3 src/zep/add.py --run_id zep
    echo -e "${GREEN}✓ Memories added successfully${NC}"
}

# Function to run zep search (answer questions)
run_zep_search() {
    echo -e "\n${GREEN}[2/3] Searching memories and generating answers...${NC}"
    python3 src/zep/search.py --run_id zep
    echo -e "${GREEN}✓ Search completed${NC}"
}

# Function to run evaluation with required metrics only
run_evaluation() {
    local input_file="$1"
    local output_file="${input_file%.json}_evaluated.json"
    local stats_file="${input_file%.json}_statistics.json"
    
    echo -e "\n${GREEN}[3/3] Evaluating results (F1, BLEU, LLM Judge, Latency)...${NC}"
    
    python3 evals.py \
        --input_file "${input_file}" \
        --output_file "${output_file}" \
        --max_workers 10
    
    echo -e "${GREEN}✓ Evaluation complete${NC}"
    echo -e "${BLUE}Results saved to: ${output_file}${NC}"
    
    # Calculate statistics
    echo -e "\n${GREEN}[Bonus] Calculating mean and variance statistics...${NC}"
    python3 calculate_statistics.py \
        --input_file "${output_file}" \
        --output_file "${stats_file}"
    
    echo -e "${GREEN}✓ Statistics complete${NC}"
    echo -e "${BLUE}Statistics saved to: ${stats_file}${NC}"
}

# Main execution based on command
case "${1:-full}" in
    "add")
        echo -e "${BLUE}Running: Zep Add (Memory Storage)${NC}"
        run_zep_add
        ;;
    
    "search")
        echo -e "${BLUE}Running: Zep Search (Question Answering)${NC}"
        run_zep_search
        ;;
    
    "eval")
        echo -e "${BLUE}Running: Evaluation Only${NC}"
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Please specify input file${NC}"
            echo -e "Usage: $0 eval results/zep_search_results.json"
            exit 1
        fi
        run_evaluation "$2"
        ;;
    
    "full")
        echo -e "${BLUE}Running: Full Benchmark (standard mode)${NC}"
        run_zep_add
        run_zep_search
        RESULT_FILE="results/zep_search_results.json"
        if [ -f "$RESULT_FILE" ]; then
            run_evaluation "$RESULT_FILE"
        else
            echo -e "${YELLOW}Warning: Result file not found at expected location${NC}"
            echo -e "Please check results/ directory for the output file"
        fi
        ;;
    
    "stats")
        echo -e "${BLUE}Running: Calculate Statistics Only${NC}"
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Please specify evaluated results file${NC}"
            echo -e "Usage: $0 stats results/zep_search_results_evaluated.json"
            exit 1
        fi
        STATS_FILE="${2%.json}_statistics.json"
        python3 calculate_statistics.py --input_file "$2" --output_file "$STATS_FILE"
        ;;
    
    "help"|"-h"|"--help")
        echo -e "Usage: $0 [command] [options]"
        echo -e ""
        echo -e "Commands:"
        echo -e "  ${GREEN}full${NC}         - Complete benchmark: add + search + eval (default)"
        echo -e "  ${GREEN}add${NC}          - Only add memories to Zep"
        echo -e "  ${GREEN}search${NC}       - Only search memories"
        echo -e "  ${GREEN}eval${NC}         - Only evaluate results [result_file]"
        echo -e "  ${GREEN}stats${NC}        - Only calculate statistics [evaluated_file]"
        echo -e ""
        echo -e "Examples:"
        echo -e "  $0 full                  # Run complete benchmark"
        echo -e "  $0 add                   # Only add memories"
        echo -e "  $0 search                # Only search/answer"
        echo -e "  $0 eval results/zep_search_results.json"
        echo -e "  $0 stats results/zep_search_results_evaluated.json"
        echo -e ""
        echo -e "Metrics evaluated:"
        echo -e "  - F1 Score (token overlap)"
        echo -e "  - BLEU Score (n-gram similarity)"
        echo -e "  - LLM Judge Score (binary correctness)"
        echo -e "  - Latency (search + response time)"
        echo -e ""
        echo -e "Output files include:"
        echo -e "  - *_evaluated.json - Full results with all metrics"
        echo -e "  - *_statistics.json - Mean, variance, std dev for all metrics"
        ;;
    
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo -e "Run '$0 help' for usage information"
        exit 1
        ;;
esac

echo -e "\n${GREEN}=== Benchmark Complete ===${NC}"

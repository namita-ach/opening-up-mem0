#!/bin/bash

# Mem0 LOCOMO Benchmark Runner
# This script runs benchmarking with Mem0 on the LOCOMO dataset
# and evaluates with F1, BLEU, LLM Score, and Latency metrics

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Mem0 LOCOMO Benchmark Runner ===${NC}\n"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo -e "Please copy .env.example to .env and fill in your API keys:"
    echo -e "  ${YELLOW}cp .env.example .env${NC}"
    exit 1
fi

# Check for required Python packages
echo -e "${BLUE}Checking dependencies...${NC}"
python3 -c "import mem0, openai, nltk" 2>/dev/null || {
    echo -e "${YELLOW}Some dependencies are missing. Installing...${NC}"
    pip install mem0ai openai python-dotenv jinja2 nltk tqdm numpy scikit-learn pandas
}

# Create results directory if it doesn't exist
mkdir -p results

# Function to run mem0 add (store memories)
run_mem0_add() {
    echo -e "\n${GREEN}[1/3] Adding memories to Mem0...${NC}"
    python3 run_experiments.py \
        --technique_type mem0 \
        --method add
    echo -e "${GREEN}✓ Memories added successfully${NC}"
}

# Function to run mem0 search (answer questions)
run_mem0_search() {
    local top_k=${1:-30}
    local filter=${2:-false}
    local graph=${3:-false}
    local category=${4:-all}
    
    echo -e "\n${GREEN}[2/3] Searching memories and generating answers...${NC}"
    if [ "$category" == "all" ]; then
        echo -e "  Top-K: ${top_k}, Filter: ${filter}, Graph: ${graph}, Category: All"
    else
        echo -e "  Top-K: ${top_k}, Filter: ${filter}, Graph: ${graph}, Category: ${category}"
    fi
    
    python3 run_experiments.py \
        --technique_type mem0 \
        --method search \
        --output_folder results/ \
        --top_k ${top_k} \
        $([ "$filter" == "true" ] && echo "--filter_memories") \
        $([ "$graph" == "true" ] && echo "--is_graph") \
        $([ "$category" != "all" ] && echo "--category ${category}")
    
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
        echo -e "${BLUE}Running: Mem0 Add (Memory Storage)${NC}"
        run_mem0_add
        ;;
    
    "search")
        echo -e "${BLUE}Running: Mem0 Search (Question Answering)${NC}"
        TOP_K=${2:-30}
        CATEGORY=${3:-all}
        run_mem0_search $TOP_K false false $CATEGORY
        ;;
    
    "eval")
        echo -e "${BLUE}Running: Evaluation Only${NC}"
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Please specify input file${NC}"
            echo -e "Usage: $0 eval results/mem0_results_top_30_filter_False_graph_False.json"
            exit 1
        fi
        run_evaluation "$2"
        ;;
    
    "quick")
        echo -e "${BLUE}Running: Quick Test (top_k=10, no graph)${NC}"
        CATEGORY=${2:-all}
        run_mem0_add
        run_mem0_search 10 false false $CATEGORY
        if [ "$CATEGORY" == "all" ]; then
            RESULT_FILE="results/mem0_results_top_10_filter_False_graph_False.json"
        else
            RESULT_FILE="results/mem0_results_top_10_filter_False_graph_False_cat${CATEGORY}.json"
        fi
        if [ -f "$RESULT_FILE" ]; then
            run_evaluation "$RESULT_FILE"
        else
            echo -e "${YELLOW}Warning: Result file not found at expected location${NC}"
            echo -e "Please check results/ directory for the output file"
        fi
        ;;
    
    "full")
        echo -e "${BLUE}Running: Full Benchmark (top_k=30, standard mode)${NC}"
        CATEGORY=${2:-all}
        run_mem0_add
        run_mem0_search 30 false false $CATEGORY
        if [ "$CATEGORY" == "all" ]; then
            RESULT_FILE="results/mem0_results_top_30_filter_False_graph_False.json"
        else
            RESULT_FILE="results/mem0_results_top_30_filter_False_graph_False_cat${CATEGORY}.json"
        fi
        if [ -f "$RESULT_FILE" ]; then
            run_evaluation "$RESULT_FILE"
        else
            echo -e "${YELLOW}Warning: Result file not found at expected location${NC}"
            echo -e "Please check results/ directory for the output file"
        fi
        ;;
    
    "graph")
        echo -e "${BLUE}Running: Full Benchmark with Graph Mode${NC}"
        run_mem0_add true
        run_mem0_search 30 false true all
        RESULT_FILE="results/mem0_results_top_30_filter_False_graph_True.json"
        if [ -f "$RESULT_FILE" ]; then
            run_evaluation "$RESULT_FILE"
        else
            echo -e "${YELLOW}Warning: Result file not found at expected location${NC}"
            echo -e "Please check results/ directory for the output file"
        fi
        ;;
    
    "by-category")
        echo -e "${BLUE}Running: Benchmark Each Category Separately${NC}"
        TOP_K=${2:-30}
        
        # Only need to add memories once
        run_mem0_add
        
        # Process each category (1-4, skip 5 as it's unanswerable)
        for cat in 1 2 3 4; do
            echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${YELLOW}Processing Category ${cat}${NC}"
            echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            
            run_mem0_search $TOP_K false false $cat
            RESULT_FILE="results/mem0_results_top_${TOP_K}_filter_False_graph_False_cat${cat}.json"
            
            if [ -f "$RESULT_FILE" ]; then
                run_evaluation "$RESULT_FILE"
            else
                echo -e "${YELLOW}Warning: Result file not found for category ${cat}${NC}"
            fi
        done
        
        echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}All categories processed!${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "\nResults saved in results/ directory with _cat[1-4] suffix"
        ;;
    
    "stats")
        echo -e "${BLUE}Running: Calculate Statistics Only${NC}"
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Please specify evaluated results file${NC}"
            echo -e "Usage: $0 stats results/mem0_results_top_30_filter_False_graph_False_evaluated.json"
            exit 1
        fi
        STATS_FILE="${2%.json}_statistics.json"
        python3 calculate_statistics.py --input_file "$2" --output_file "$STATS_FILE"
        ;;
    
    "help"|"-h"|"--help")
        echo -e "Usage: $0 [command] [options]"
        echo -e ""
        echo -e "Commands:"
        echo -e "  ${GREEN}full${NC}         - Complete benchmark: add + search + eval (default) [category]"
        echo -e "  ${GREEN}quick${NC}        - Quick test with top_k=10 [category]"
        echo -e "  ${GREEN}graph${NC}        - Full benchmark with graph-based memory"
        echo -e "  ${GREEN}by-category${NC}  - Run benchmark for each category separately [top_k]"
        echo -e "  ${GREEN}add${NC}          - Only add memories to Mem0"
        echo -e "  ${GREEN}search${NC}       - Only search memories [top_k] [category]"
        echo -e "  ${GREEN}eval${NC}         - Only evaluate results [result_file]"
        echo -e "  ${GREEN}stats${NC}        - Only calculate statistics [evaluated_file]"
        echo -e ""
        echo -e "Categories:"
        echo -e "  1 - Explicit statements (direct mentions)"
        echo -e "  2 - Implicit statements (inferred information)"
        echo -e "  3 - Event sequence (temporal ordering)"
        echo -e "  4 - Reasoning (logical deduction)"
        echo -e "  5 - Unanswerable (insufficient information) [auto-skipped]"
        echo -e "  all - All categories (default)"
        echo -e ""
        echo -e "Examples:"
        echo -e "  $0 full                  # Run complete benchmark (all categories)"
        echo -e "  $0 full 2                # Run benchmark only for category 2"
        echo -e "  $0 quick 1               # Quick test with category 1"
        echo -e "  $0 by-category           # Run each category separately (top_k=30)"
        echo -e "  $0 by-category 20        # Run each category separately (top_k=20)"
        echo -e "  $0 search 20 3           # Search with top_k=20, category 3"
        echo -e "  $0 stats results/mem0_results_top_30_filter_False_graph_False_evaluated.json"
        echo -e "  $0 eval results/mem0_results_top_30_filter_False_graph_False_cat2.json"
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

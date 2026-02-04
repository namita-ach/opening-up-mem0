#!/usr/bin/env python3
"""
Calculate Mean and Variance Statistics for Benchmark Metrics

This script processes evaluated benchmark results and calculates:
- Mean (average)
- Variance
- Standard deviation
- Min/Max values
- Count

for all measured metrics across all questions and categories.
"""

import argparse
import json
import statistics
from collections import defaultdict
from typing import Dict, List, Any


def calculate_stats(values: List[float]) -> Dict[str, float]:
    """Calculate comprehensive statistics for a list of values."""
    if not values:
        return {
            "count": 0,
            "mean": 0.0,
            "variance": 0.0,
            "std_dev": 0.0,
            "min": 0.0,
            "max": 0.0,
        }
    
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "variance": statistics.variance(values) if len(values) > 1 else 0.0,
        "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def collect_metrics(data: Dict[str, List[Dict]]) -> Dict[str, Dict[str, List[float]]]:
    """Collect all metric values organized by category and overall."""
    metrics_by_category = defaultdict(lambda: defaultdict(list))
    
    # Metrics to collect
    metric_names = [
        "f1_score",
        "bleu_score",
        "llm_score",
        "search_time",
        "response_time",
        "total_latency",
    ]
    
    # Collect values for all categories and overall
    for conversation_idx, questions in data.items():
        for question_data in questions:
            category = question_data.get("category", "unknown")
            
            # Collect for this specific category
            for metric in metric_names:
                if metric in question_data:
                    value = question_data[metric]
                    # Handle None values
                    if value is not None:
                        metrics_by_category[f"category_{category}"][metric].append(float(value))
                        # Also add to overall
                        metrics_by_category["overall"][metric].append(float(value))
    
    return metrics_by_category


def format_stats_table(stats: Dict[str, Dict[str, Any]]) -> str:
    """Format statistics as a readable table."""
    output = []
    
    for group_name, group_stats in sorted(stats.items()):
        output.append(f"\n{'='*80}")
        output.append(f"{group_name.upper()}")
        output.append('='*80)
        
        if not group_stats:
            output.append("No data available")
            continue
        
        # Header
        output.append(f"{'Metric':<20} {'Count':<8} {'Mean':<12} {'Variance':<12} {'Std Dev':<12} {'Min':<10} {'Max':<10}")
        output.append('-'*80)
        
        # Sort metrics for consistent display
        metric_order = ["f1_score", "bleu_score", "llm_score", "search_time", "response_time", "total_latency"]
        sorted_metrics = sorted(group_stats.keys(), key=lambda x: metric_order.index(x) if x in metric_order else 999)
        
        for metric_name in sorted_metrics:
            metric_stats = group_stats[metric_name]
            output.append(
                f"{metric_name:<20} "
                f"{metric_stats['count']:<8} "
                f"{metric_stats['mean']:<12.4f} "
                f"{metric_stats['variance']:<12.4f} "
                f"{metric_stats['std_dev']:<12.4f} "
                f"{metric_stats['min']:<10.4f} "
                f"{metric_stats['max']:<10.4f}"
            )
    
    return '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Calculate mean and variance statistics for benchmark metrics"
    )
    parser.add_argument(
        "--input_file",
        type=str,
        required=True,
        help="Path to the evaluated results JSON file"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default=None,
        help="Path to save statistics JSON file (optional)"
    )
    parser.add_argument(
        "--show_table",
        action="store_true",
        default=True,
        help="Display statistics as a formatted table (default: True)"
    )
    
    args = parser.parse_args()
    
    # Load the evaluated results
    print(f"\nLoading results from: {args.input_file}")
    with open(args.input_file, 'r') as f:
        data = json.load(f)
    
    # Collect metrics by category
    print("Collecting metrics...")
    metrics_by_category = collect_metrics(data)
    
    # Calculate statistics for each category and overall
    print("Calculating statistics...")
    all_statistics = {}
    
    for group_name, metrics_dict in metrics_by_category.items():
        all_statistics[group_name] = {}
        for metric_name, values in metrics_dict.items():
            all_statistics[group_name][metric_name] = calculate_stats(values)
    
    # Display as table
    if args.show_table:
        print(format_stats_table(all_statistics))
    
    # Save to file if specified
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump(all_statistics, f, indent=4)
        print(f"\nStatistics saved to: {args.output_file}")
    
    # Quick summary
    print("\n" + "="*80)
    print("QUICK SUMMARY")
    print("="*80)
    
    if "overall" in all_statistics:
        overall = all_statistics["overall"]
        
        print("\nKey Metrics (Overall):")
        if "f1_score" in overall:
            print(f"  F1 Score:       {overall['f1_score']['mean']:.4f} ± {overall['f1_score']['std_dev']:.4f}")
        if "bleu_score" in overall:
            print(f"  BLEU Score:     {overall['bleu_score']['mean']:.4f} ± {overall['bleu_score']['std_dev']:.4f}")
        if "llm_score" in overall:
            print(f"  LLM Accuracy:   {overall['llm_score']['mean']:.4f} ± {overall['llm_score']['std_dev']:.4f}")
        if "total_latency" in overall:
            print(f"  Total Latency:  {overall['total_latency']['mean']:.4f}s ± {overall['total_latency']['std_dev']:.4f}s")
        
        print(f"\nTotal Questions: {overall[list(overall.keys())[0]]['count']}")
    
    # Category breakdown
    categories = [k for k in all_statistics.keys() if k.startswith("category_")]
    if categories:
        print(f"\nCategories Analyzed: {len(categories)}")
        for cat in sorted(categories):
            cat_num = cat.replace("category_", "")
            count = all_statistics[cat][list(all_statistics[cat].keys())[0]]['count']
            print(f"  Category {cat_num}: {count} questions")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()

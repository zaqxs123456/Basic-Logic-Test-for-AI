import os
import json
import glob
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

def load_questions():
    """Load questions from questions.json"""
    with open("questions.json", "r") as f:
        return json.load(f)

def find_result_files(results_dir="results"):
    """Find all result files in the directory"""
    if not os.path.exists(results_dir):
        print(f"❌ No results directory found at path: {os.path.abspath(results_dir)}")
        return []
    
    # Get all result files
    result_files = glob.glob(f"{results_dir}/results_*.json")
    print(f"Found {len(result_files)} result files in directory: {os.path.abspath(results_dir)}")
    
    if not result_files and os.path.exists(results_dir):
        # Debug info if no files found with pattern
        all_files = os.listdir(results_dir)
        print(f"Files in directory: {all_files}")
        
    return result_files

def extract_model_and_timestamp(filename):
    """Extract model name and timestamp from a filename"""
    basename = os.path.basename(filename)
    
    # Try different patterns to extract information
    patterns = [
        r"results_(.+?)_(\d{8}-\d{6})\.json$",  # Standard format with hyphenated timestamp
        r"results_([^_]+)_(.+?)\.json$"         # More generic fallback pattern
    ]
    
    for pattern in patterns:
        match = re.search(pattern, basename)
        if match:
            model_name, timestamp = match.groups()
            timestamp_clean = timestamp.replace("-", "")  # Normalize for comparison
            return model_name, timestamp_clean
    
    # Fallback if no pattern matches
    print(f"  ⚠️ Using fallback: treating whole file as one result")
    model_name = basename.replace("results_", "").replace(".json", "")
    return model_name, "0"  # Use "0" as timestamp to rank it last

def get_latest_results_by_model():
    """Find the latest result file for each model"""
    result_files = find_result_files()
    if not result_files:
        return {}
    
    # Process each file to extract model and timestamp
    model_results = {}
    for file_path in result_files:
        model_name, timestamp = extract_model_and_timestamp(file_path)
        
        # Keep only the latest result for each model
        if model_name not in model_results or timestamp > model_results[model_name][0]:
            model_results[model_name] = (timestamp, file_path)
    
    # Return only the file paths for the latest results
    latest_results = {model: data[1] for model, data in model_results.items()}
    
    if not latest_results:
        print("❌ No result files found matching the pattern")
    else:
        print(f"✅ Found latest results for {len(latest_results)} models")
        for model, file_path in latest_results.items():
            print(f"  - {model}: {os.path.basename(file_path)}")
    
    return latest_results

def load_result(file_path):
    """Load a result file"""
    with open(file_path, "r") as f:
        return json.load(f)

def format_model_name(model_name, metadata=None):
    """Format model name for display"""
    # Check if there's a custom display name in metadata
    if metadata and metadata.get("display_name"):
        return metadata.get("display_name")
        
    # Otherwise use the default formatting
    display_name = model_name.split(':')[0].capitalize()
    return display_name

def create_table_header(questions):
    """Create the header section of the table"""
    header = "# AI Model Logical Reasoning Test Results\n\n"
    header += "Generated on: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n"
    
    # Add explanation of table notation
    header += "## How to Read This Table\n\n"
    header += "- **Question results:** ✅ 5/5(4) means a correct answer with score 5 out of 5, taking 4 attempts to get it right\n"
    header += "- **Question results:** ❌ 0/5(3) means an incorrect answer with score 0, despite 3 attempts\n"
    header += "- **Question results:** ❌ 0/5(5)⏱️ means the last attempt timed out\n"
    header += "- **Overall results:** 50.0% (3.7 tries) means the model answered 50% of questions correctly, with an average of 3.7 attempts per question\n\n"
    
    # Create header row with links to questions and answers
    row = "| Model | "
    for q in questions:
        short_name = q.get("short_name", f"Q{questions.index(q)+1}")
        q_rel_path = os.path.normpath(q["question"])
        a_rel_path = os.path.normpath(q["answer"])
        
        # Create the header cell with links
        row += f"[{short_name}]({q_rel_path})<br>([Answer]({a_rel_path})) | "
    
    # Add total score and percentage columns
    row += "Total | % |\n"
    
    # Add separator row
    separator = "| --- |" + " :---: |" * (len(questions) + 2) + "\n"
    
    return header + row + separator

def format_question_result(q_result, q_index):
    """Format a single question result cell for the table"""
    if not q_result:
        return "N/A | "
    
    assessment = q_result.get("assessment", "N/A").lower()
    best_score = q_result.get("best_score", 0)
    attempts = q_result.get("attempts", 1)
    is_timeout = q_result.get("timeout", False)
    
    # Add emoji based on assessment - use lowercase assessment
    emoji = "✅" if assessment == "correct" else "❌"
    
    # Add attempt information if multiple attempts were made
    attempts_info = f"({attempts})" if attempts > 1 else ""
    
    # Add timeout indicator
    timeout_indicator = "⏱️" if is_timeout else ""
    
    return f"{emoji} {best_score}/5{attempts_info}{timeout_indicator} | "

def create_model_rows(model_scores, questions, latest_results):
    """Create table rows for each model's performance"""
    rows = ""
    
    for model, result_file, _ in model_scores:
        result = load_result(result_file)
        metadata = result.get("metadata", {})
        results = result.get("results", [])
        
        # Format model name, passing metadata to use display name if available
        display_model = format_model_name(model, metadata)
        
        # Start the row with the model name
        row = f"| {display_model} | "
        
        # Add a cell for each question
        for q in questions:
            q_index = questions.index(q) + 1
            
            # Find the corresponding result
            q_result = next(
                (r for r in results if r.get("question_index") == q_index or r.get("question_path") == q["question"]), 
                None
            )
            
            row += format_question_result(q_result, q_index)
        
        # Add total score and percentage
        total_score = metadata.get("total_score", 0)
        max_score = metadata.get("max_possible_score", 0)
        correct_percentage = metadata.get("correct_percentage", 0)
        avg_attempts = metadata.get("avg_attempts", 1)
        
        if max_score > 0:
            row += f"{total_score}/{max_score} | {correct_percentage:.1f}% ({avg_attempts:.1f} tries) |\n"
        else:
            row += "N/A | N/A |\n"
        
        rows += row
    
    return rows

def calculate_question_statistics(latest_results):
    """Calculate success rates and average attempts for each question across models"""
    question_stats = {}
    
    for model_name, result_file in latest_results.items():
        result = load_result(result_file)
        for item in result.get("results", []):
            q_index = item.get("question_index")
            if q_index not in question_stats:
                question_stats[q_index] = {"attempts": [], "successes": 0, "total": 0}
            
            question_stats[q_index]["attempts"].append(item.get("attempts", 1))
            # Use lowercase assessment and handle "wong" too
            assessment = item.get("assessment", "").lower()
            question_stats[q_index]["successes"] += 1 if assessment == "correct" else 0
            question_stats[q_index]["total"] += 1
    
    return question_stats

def create_performance_table(questions, question_stats):
    """Create a table showing performance statistics for each question"""
    table = "\n## Question Performance\n\n"
    table += "| Question | Human | AI | Success Rate | Avg Attempts |\n"
    table += "| --- | :---: | :---: | :---: | :---: |\n"
    
    for q in questions:
        q_index = questions.index(q) + 1
        short_name = q.get("short_name", f"Q{q_index}")
        human_difficulty = "⭐" * int(q["human_difficulty"])
        ai_difficulty = "⭐" * int(q["ai_difficulty"])
        
        stats = question_stats.get(q_index, {"attempts": [1], "successes": 0, "total": 0})
        success_rate = (stats["successes"] / stats["total"] * 100) if stats["total"] > 0 else 0
        avg_attempts = sum(stats["attempts"]) / len(stats["attempts"]) if stats["attempts"] else 1
        
        table += f"| {short_name} | {human_difficulty} | {ai_difficulty} | {success_rate:.1f}% | {avg_attempts:.1f} |\n"
    
    return table

def generate_table():
    """Generate a results table in markdown format"""
    questions = load_questions()
    latest_results = get_latest_results_by_model()
    
    if not latest_results:
        return None
    
    # Generate table header
    table = create_table_header(questions)
    
    # Sort models by score percentage
    model_scores = []
    for model, result_file in latest_results.items():
        result = load_result(result_file)
        metadata = result.get("metadata", {})
        score_percentage = metadata.get("score_percentage", 0)
        model_scores.append((model, result_file, score_percentage))
    
    # Sort by score (descending)
    model_scores.sort(key=lambda x: x[2], reverse=True)
    
    # Add rows for each model
    table += create_model_rows(model_scores, questions, latest_results)
    
    # Calculate question statistics
    question_stats = calculate_question_statistics(latest_results)
    
    # Add performance table
    table += create_performance_table(questions, question_stats)
    
    return table

def update_readme_with_table(table_content):
    """Update the README.md file with the latest results table"""
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        print(f"❌ README file not found at {readme_path}")
        return False
    
    # Read the current README content
    with open(readme_path, 'r') as f:
        readme_content = f.read()
    
    # Define markers for the results section
    begin_marker = "<!-- BEGIN_RESULTS_TABLE -->"
    end_marker = "<!-- END_RESULTS_TABLE -->"
    
    # Check if markers exist
    if begin_marker not in readme_content:
        # Find the section header
        results_header = "## AI Model Logical Reasoning Test Results"
        if results_header not in readme_content:
            print(f"❌ Could not find section '{results_header}' in README.md")
            return False
            
        # Add markers after the section header
        readme_content = readme_content.replace(
            results_header,
            f"{results_header}\n\n{begin_marker}\n{end_marker}"
        )
    
    # Replace content between markers
    pattern = re.compile(f"{begin_marker}.*?{end_marker}", re.DOTALL)
    updated_content = pattern.sub(f"{begin_marker}\n{table_content}\n{end_marker}", readme_content)
    
    # Write updated content back to README
    with open(readme_path, 'w') as f:
        f.write(updated_content)
    
    print(f"✅ Updated README.md with latest results table")
    return True

def main():
    """Main function"""
    print("🔍 Generating results table...")
    table = generate_table()
    
    if not table:
        print("❌ Could not generate table")
        return
    
    # Write table to file
    output_file = "results_table.md"
    with open(output_file, "w") as f:
        f.write(table)
    
    print(f"✅ Results table saved to {output_file}")
    
    # Update README with table content
    # Extract just the table part (skip the header and explanation)
    table_lines = table.strip().split("\n")
    section_start = next((i for i, line in enumerate(table_lines) if line.startswith("| Model |")), 0)
    if section_start > 0:
        section_start -= 1  # Include the header line
    results_section = "\n".join(table_lines[section_start:])
    update_readme_with_table(results_section)

if __name__ == "__main__":
    main()

import json
import os
from datetime import datetime

def load_questions():
    """Load questions from questions.json"""
    with open("questions.json", "r") as f:
        return json.load(f)

def read_file_content(file_path):
    """Read content from a file"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_path, file_path)
    try:
        with open(full_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def get_difficulty_stars(difficulty_level):
    """Convert difficulty level to star emojis"""
    try:
        level = int(difficulty_level)
        return "⭐" * level
    except (ValueError, TypeError):
        return "⭐"  # Default to one star if conversion fails

def get_difficulty_emoji(difficulty_level):
    """Get difficulty emoji based on level"""
    try:
        level = int(difficulty_level)
        if level <= 1:
            return "🟢 Easy"  # Green: Easy
        elif level <= 3:
            return "🟡 Medium"  # Yellow: Medium
        else:
            return "🔴 Hard"  # Red: Hard
    except (ValueError, TypeError):
        return "⚪ Unknown"  # White: Unknown

def create_table_of_contents(questions):
    """Create a table of contents for the questions"""
    toc = "## Table of Contents 📋\n\n"
    toc += "| # | Question | AI Difficulty | Human Difficulty |\n"
    toc += "|---|----------|---------------|------------------|\n"
    for i, q in enumerate(questions, 1):
        short_name = q.get("short_name", f"Question {i}")
        human_difficulty = get_difficulty_emoji(q.get("human_difficulty", "3"))
        ai_difficulty = get_difficulty_emoji(q.get("ai_difficulty", "3"))
        
        toc += f"| 1 | [{short_name}](#question-{i}) | {ai_difficulty} | {human_difficulty}\n"
    return toc

def create_question_section(index, question):
    """Create a formatted section for a question and answer"""
    short_name = question.get("short_name", f"Question {index}")
    question_path = question["question"]
    answer_path = question["answer"]
    
    human_difficulty = question.get("human_difficulty", "3")
    ai_difficulty = question.get("ai_difficulty", "3")
    
    human_stars = get_difficulty_stars(human_difficulty)
    ai_stars = get_difficulty_stars(ai_difficulty)
    
    # Read question and answer content
    question_content = read_file_content(question_path)
    answer_content = read_file_content(answer_path)
    
    section = f"## Question {index}: {short_name} <a name=\"question-{index}\"></a>\n\n"
    section += f"### 📊 Difficulty\n\n"
    section += f"- 👤 Human: {human_difficulty}/5 {human_stars}\n"
    section += f"- 🤖 AI: {ai_difficulty}/5 {ai_stars}\n\n"
    
    section += f"### ❓ Question\n\n"
    section += f"{question_content}\n\n"
    
    section += f"### ✅ Expected Answer\n\n"
    section += f"{answer_content}\n\n"
    
    section += "---\n\n"
    
    return section

def generate_questions_markdown():
    """Generate a markdown file with all questions and answers"""
    questions = load_questions()
    
    markdown = "# 🧠 AI Logical Reasoning Test Questions & Answers 🧠\n\n"
    markdown += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    markdown += "This document contains all questions and reference answers used in the test.\n\n"
    
    # Add table of contents
    markdown += create_table_of_contents(questions)
    markdown += "\n---\n\n"
    
    # Add each question and answer
    for i, question in enumerate(questions, 1):
        markdown += create_question_section(i, question)
    
    return markdown

def main():
    """Main function"""
    print("🔍 Generating questions summary...")
    questions_md = generate_questions_markdown()
    
    # Write to file
    output_file = "questions.md"
    with open(output_file, "w") as f:
        f.write(questions_md)
    
    print(f"✅ Questions summary saved to {output_file}")

if __name__ == "__main__":
    main()

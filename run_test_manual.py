import argparse
import json
import os
import time
import sys
import subprocess

# Import functions from run_test.py
from run_test import (
    load_questions, 
    read_file_content,
    evaluate_answer,
    evaluate_with_double_check,
    get_difficulty_stars,
    parse_evaluation,
    check_model_exists,
    pull_model_with_progress
)

def display_question(question_content, short_name, q_index, total_questions, 
                    human_difficulty, ai_difficulty):
    """Display a question to the user for manual answering"""
    print(f"\n{'='*80}")
    print(f"📝 Question {q_index}/{total_questions}: {short_name}")
    
    # Print difficulty info
    human_difficulty_stars = get_difficulty_stars(human_difficulty)
    ai_difficulty_stars = get_difficulty_stars(ai_difficulty)
    
    print(f"👤 Human difficulty: {human_difficulty}/5 {human_difficulty_stars}")
    print(f"🤖 AI difficulty: {ai_difficulty}/5 {ai_difficulty_stars}")
    
    # Display question content
    print("\n❓ QUESTION TO COPY:")
    print("-"*40)
    print(question_content)
    print("-"*40)

def get_manual_answer(attempt_num=1):
    """Get manual answer from user input"""
    print(f"\n📝 {f'Attempt {attempt_num}/5' if attempt_num > 1 else 'First attempt'}")
    print("\n🔍 Please paste the model's response below.")
    print("Type 'END' on a new line to finish, or 'SKIP' to skip this question:")
    print("-"*40)
    
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        if line.strip() == "SKIP":
            return "[SKIPPED]"
        lines.append(line)
    
    return "\n".join(lines)

def process_question_attempt_manual(model_name, evaluator1_model, evaluator2_model, 
                                  question_content, model_answer_content, attempt_num=1):
    """Process a single manual attempt at answering a question"""
    # Get the answer from user input
    user_answer = get_manual_answer(attempt_num)
    
    # Check if skipped
    if user_answer == "[SKIPPED]":
        print("⏭️ Attempt skipped.")
        return {
            "answer": user_answer,
            "evaluation": "[SKIPPED]",
            "assessment": "wrong",  # Count skips as wrong
            "score": 0,
            "consensus": True
        }
    
    print(f"\n📢 {model_name}'s answer (pasted):\n{user_answer[:200]}...")
    
    # Use double evaluation if second evaluator is provided
    if evaluator2_model:
        result = evaluate_with_double_check(
            evaluator1_model,
            evaluator2_model,
            user_answer,
            model_answer_content,
            question_content
        )
        result["answer"] = user_answer
    else:
        # Fall back to single evaluator if no second evaluator
        evaluation = evaluate_answer(
            evaluator1_model,
            user_answer,
            model_answer_content,
            question_content
        )
        
        # Parse the evaluation
        assessment, score = parse_evaluation(evaluation)
        
        result = {
            "answer": user_answer,
            "evaluation": evaluation,
            "assessment": assessment,
            "score": score,
            "consensus": True  # Mark as consensus since only one evaluator
        }
    
    # Display results
    result_emoji = "✅" if result["assessment"] == "correct" else "❌"
    consensus_icon = "🤝" if result.get("consensus", False) else "⚔️"
    print(f"\n{result_emoji} Assessment: {result['assessment']} {consensus_icon}")
    print(f"🏅 Score: {result['score']}/5 {get_difficulty_stars(result['score'])}")
    print(f"📊 Evaluation summary:\n{result['evaluation'].split('\n')[0]}...")
    
    return result

def handle_question_manual(model_name, evaluator1_model, evaluator2_model, question_data, 
                         q_index, total_questions, max_attempts=5):
    """Handle the full process of manually asking and evaluating a question"""
    question_path = question_data["question_path"]
    answer_path = question_data["answer_path"]
    short_name = question_data.get("short_name", f"Q{q_index}")
    human_difficulty = question_data.get("human_difficulty", "3")
    ai_difficulty = question_data.get("ai_difficulty", "3")
    
    # Load question and answer content
    question_content = read_file_content(question_path)
    model_answer_content = read_file_content(answer_path)
    
    # Display the question to the user
    display_question(
        question_content, 
        short_name, 
        q_index, 
        total_questions,
        human_difficulty,
        ai_difficulty
    )
    
    # Initialize result tracking
    test_subject_answers = []
    evaluations = []
    scores = []
    assessments = []
    attempts = 0
    success = False
    attempts_until_success = None
    
    # Process attempts
    for attempt in range(1, max_attempts + 1):
        # Process the attempt
        result = process_question_attempt_manual(
            model_name,
            evaluator1_model,
            evaluator2_model,
            question_content,
            model_answer_content,
            attempt
        )
        
        # Skip the entire question if the attempt was skipped
        if result["answer"] == "[SKIPPED]":
            print("⏭️ Question skipped - moving to next question")
            attempts = 1
            # Return a basic result for the skipped question
            return {
                "question_index": q_index,
                "question_path": question_path,
                "answer_path": answer_path,
                "short_name": short_name,
                "test_subject_answers": ["[SKIPPED]"],
                "evaluations": ["[SKIPPED - No evaluation performed]"],
                "scores": [0],
                "attempts": 1,
                "attempts_until_success": None,
                "assessment": "skipped",  # Mark as skipped rather than wrong
                "best_score": 0,
                "timeout": False
            }
        
        # Record results
        test_subject_answers.append(result["answer"])
        evaluations.append(result["evaluation"])
        scores.append(result["score"])
        assessments.append(result["assessment"])
        attempts = attempt
        
        # Check if successful
        if result["assessment"] == "correct":
            success = True
            attempts_until_success = attempt
            if attempt == 1:
                print("✅ Success on first attempt!")
            else:
                print(f"✅ Success on attempt {attempts_until_success}!")
            
            # Ask if user wants to continue with more attempts
            if attempt < max_attempts:
                choice = input("\n✅ Success achieved! Try more attempts to improve score? (y/n): ")
                if choice.lower() != 'y':
                    print("✓ Moving to next question.")
                    break
                print("✓ Continuing with additional attempts to improve score.")
            else:
                break
        
        # For unsuccessful attempts
        if attempt == 1:
            print("❌ Incorrect. Will try again.")
        elif attempt < max_attempts:
            print(f"❌ Still incorrect. Trying again...")
        else:
            print(f"❌ Still incorrect. No more attempts.")
    
    # Find best score
    best_score = max(scores) if scores else 0
    
    # Create final result object - use lowercase for setting assessment
    final_result = {
        "question_index": q_index,
        "question_path": question_path,
        "answer_path": answer_path,
        "short_name": short_name,
        "test_subject_answers": test_subject_answers,
        "evaluations": evaluations,
        "scores": scores,
        "attempts": attempts,
        "attempts_until_success": attempts_until_success,
        "assessment": "correct" if success else "wrong",  # Use lowercase
        "best_score": best_score,
        "timeout": False  # No timeouts in manual mode
    }
    
    return final_result

def run_test_manual(model_name, evaluator1_model, evaluator2_model=None, max_attempts=5):
    """Run the test with questions from json file in manual mode"""
    questions = load_questions("questions.json")
    results = []
    
    print(f"\n🧠 Running manual test for {model_name}, evaluated by {evaluator1_model}" + 
          (f" and {evaluator2_model}" if evaluator2_model else "") + " 🧠\n")
    
    print("📋 INSTRUCTIONS:")
    print("1. Copy each question and paste it to your model")
    print("2. Copy the model's response and paste it back here")
    print("3. Type 'END' on a new line after pasting the response")
    print("4. Type 'SKIP' to skip an attempt\n")
    
    total_questions = len(questions)
    questions_to_process = list(range(1, total_questions + 1))
    
    # Ask if user wants to process specific questions
    question_choice = input("Process all questions or specific ones? Enter question numbers separated by commas, or 'all': ")
    if question_choice.lower() != 'all':
        try:
            chosen_indices = [int(idx.strip()) for idx in question_choice.split(',')]
            questions_to_process = [idx for idx in chosen_indices if 1 <= idx <= total_questions]
            print(f"Will process {len(questions_to_process)} questions: {questions_to_process}")
        except ValueError:
            print("Invalid input. Processing all questions.")
    
    # Process each selected question
    for index in questions_to_process:
        i = index - 1  # Convert to 0-based index for the list
        q = questions[i]
        
        # Prepare question data dictionary with all needed fields
        question_data = {
            "question_path": q["question"],
            "answer_path": q["answer"],
            "short_name": q.get("short_name", f"Q{index}"),
            "human_difficulty": q.get("human_difficulty", "3"),
            "ai_difficulty": q.get("ai_difficulty", "3")
        }
        
        # Handle the question (ask, evaluate, retry if needed)
        result = handle_question_manual(
            model_name, 
            evaluator1_model,
            evaluator2_model, 
            question_data, 
            index,  # Use 1-based indexing for display
            total_questions,
            max_attempts
        )
        
        results.append(result)
        
        # Offer to save results after each question
        save_choice = input("\nSave results so far? (y/n): ")
        if save_choice.lower() == 'y':
            save_results(model_name, evaluator1_model, evaluator2_model, results)
    
    # Calculate statistics based on best attempts
    processed_count = len(results)
    best_scores = [r["best_score"] for r in results]
    total_score = sum(best_scores)
    max_score = 5 * processed_count
    skipped_count = sum(1 for r in results if r.get("assessment") == "skipped")
    correct_count = sum(1 for r in results if r["assessment"] == "correct")
    total_attempts = sum(r["attempts"] for r in results)
    
    percentage = (total_score / max_score) * 100 if max_score > 0 else 0
    correct_percentage = (correct_count / processed_count) * 100 if processed_count > 0 else 0
    avg_attempts = total_attempts / processed_count if processed_count > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"\n🎯 Final Results for {model_name} (Best of {max_attempts} attempts):")
    print(f"📊 Questions processed: {processed_count}/{total_questions}")
    if skipped_count > 0:
        print(f"⏭️ Questions skipped: {skipped_count}/{processed_count}")
    print(f"📊 Correct answers: {correct_count}/{processed_count} ({correct_percentage:.1f}%)")
    print(f"🏅 Final Score: {total_score}/{max_score} ({percentage:.1f}%) {get_difficulty_stars(round(percentage/20))}")
    print(f"🔄 Total attempts: {total_attempts} (avg: {avg_attempts:.1f} per question)")
    
    # Create metadata
    metadata = {
        "test_model": model_name,
        "display_name": model_name,
        "evaluator1_model": evaluator1_model,
        "evaluator2_model": evaluator2_model,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_score": total_score,
        "max_possible_score": max_score,
        "score_percentage": percentage,
        "correct_answers": correct_count,
        "total_questions": processed_count,
        "correct_percentage": correct_percentage,
        "total_attempts": total_attempts,
        "avg_attempts": avg_attempts,
        "max_attempts_allowed": max_attempts,
        "manual_mode": True  # Mark as manual mode
    }
    
    return results, metadata

def save_results(model_name, evaluator1_model, evaluator2_model, results):
    """Save results to a file"""
    # Calculate statistics
    processed_count = len(results)
    if processed_count == 0:
        print("❌ No results to save")
        return
    
    best_scores = [r["best_score"] for r in results]
    total_score = sum(best_scores)
    max_score = 5 * processed_count
    correct_count = sum(1 for r in results if r["assessment"] == "correct")
    total_attempts = sum([r["attempts"] for r in results])
    
    percentage = (total_score / max_score) * 100 if max_score > 0 else 0
    correct_percentage = (correct_count / processed_count) * 100 if processed_count > 0 else 0
    avg_attempts = total_attempts / processed_count if processed_count > 0 else 0
    
    # Create metadata
    metadata = {
        "test_model": model_name,
        "display_name": model_name,
        "evaluator1_model": evaluator1_model,
        "evaluator2_model": evaluator2_model,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_score": total_score,
        "max_possible_score": max_score,
        "score_percentage": percentage,
        "correct_answers": correct_count,
        "total_questions": processed_count,
        "correct_percentage": correct_percentage,
        "total_attempts": total_attempts,
        "avg_attempts": avg_attempts,
        "manual_mode": True  # Mark as manual mode
    }
    
    # Combine results and metadata
    final_results = {
        "metadata": metadata,
        "results": results
    }
    
    # Save to dedicated folder
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)
    results_file = f"{results_dir}/results_{model_name}_manual_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2)
    
    print(f"\n💾 Results saved to {results_file}")
    
    return results_file

def main():
    parser = argparse.ArgumentParser(description='Run Basic Logic Test for AI in Manual Mode')
    parser.add_argument('--model-name', '-m', required=True, help='Name of the model being tested')
    parser.add_argument('--evaluator', '-e', default='deepseek-r1:14b', 
                      help='Primary evaluator model (default: deepseek-r1:14b)')
    parser.add_argument('--evaluator2', '-e2', default='mistral-small',
                      help='Second evaluator model for consensus (default: mistral-small)')
    parser.add_argument('--attempts', '-a', type=int, default=5, 
                      help='Maximum attempts per question (default: 5)')
    parser.add_argument('--no-table', '-n', action='store_true', 
                      help='Skip generating results table')
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print(f"🚀 Starting manual test for model: {args.model_name}")
    print(f"{'='*80}\n")
    
    # Check if evaluator models exist and pull if needed
    if not check_model_exists(args.evaluator):
        pull_model_with_progress(args.evaluator)
    else:
        print(f"✓ {args.evaluator} model already exists")
    
    if args.evaluator2:
        if not check_model_exists(args.evaluator2):
            pull_model_with_progress(args.evaluator2)
        else:
            print(f"✓ {args.evaluator2} model already exists")
    
    # Run test in manual mode
    try:
        results, metadata = run_test_manual(
            args.model_name,
            args.evaluator,
            args.evaluator2,
            args.attempts
        )
        
        # Save final results
        results_file = save_results(args.model_name, args.evaluator, args.evaluator2, results)
        
        print(f"\n{'='*80}")
        print(f"✅ Test completed for model: {args.model_name}")
        print(f"{'='*80}")
        
        # Generate results table if requested
        if not args.no_table:
            try:
                print("\n📊 Generating updated results table...")
                # Run the generate_results_table.py script as a subprocess
                result = subprocess.run([sys.executable, "generate_results_table.py"], 
                                        capture_output=True, text=True, check=False)
                
                if result.returncode == 0:
                    print("✅ Results table generated successfully")
                    for line in result.stdout.splitlines():
                        if line.startswith("✅"):
                            print(line)
                else:
                    print("❌ Failed to generate results table")
                    print(f"Error: {result.stderr}")
            except Exception as e:
                print(f"❌ Error generating results table: {e}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user.")
        choice = input("Save partial results? (y/n): ")
        if choice.lower() == 'y' and 'results' in locals():
            save_results(args.model_name, args.evaluator, args.evaluator2, results)
    
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        if 'results' in locals() and len(results) > 0:
            choice = input("Save partial results? (y/n): ")
            if choice.lower() == 'y':
                save_results(args.model_name, args.evaluator, args.evaluator2, results)
    
    print("\n🏁 Manual testing session complete! 🏁")

if __name__ == "__main__":
    main()

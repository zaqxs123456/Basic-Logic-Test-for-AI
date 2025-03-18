# 🧠 AI Logical Reasoning Test Questions & Answers 🧠

Generated on: 2025-03-18 04:44:27

This document contains all questions and reference answers used in the test.

## Table of Contents 📋

| # | Question | AI Difficulty | Human Difficulty |
|---|----------|---------------|------------------|
| 1 | [Lottery System](#question-1) | 🟢 Easy | 🔴 Hard
| 1 | [Zoo Animal](#question-2) | 🟡 Medium | 🔴 Hard
| 1 | [Revenue Drop](#question-3) | 🟡 Medium | 🟡 Medium
| 1 | [Blood Pressure](#question-4) | 🔴 Hard | 🟡 Medium
| 1 | [Philosophers Logic](#question-5) | 🔴 Hard | 🔴 Hard
| 1 | [Number Sequence](#question-6) | 🔴 Hard | 🟡 Medium

---

## Question 1: Lottery System <a name="question-1"></a>

### 📊 Difficulty

- 👤 Human: 4/5 ⭐⭐⭐⭐
- 🤖 AI: 1/5 ⭐

### ❓ Question

- Tom developed a "foolproof system" for predicting lottery numbers by analyzing patterns in lottery results from last 3 months. He then tested his system against the last month results and found it correctly "predicted" the winning numbers with 80% accuracy. Excited by his success, Tom used his system to buy lottery tickets for the next 10 drawings, but none of his predictions won anything significant. 

- Why do you think Tom's system worked so well on paper, even though lottery numbers are supposed to be random? And why even it have 80% accuracy, it failed to predict the winning numbers in practice? Write your answer below.

### ✅ Expected Answer

- Tom's system appeared to work well on past data because he was overfitting his model to already known results. This is called retrospective analysis or "overfitting" - when you create a model that works extremely well on historical data because it captures both the genuine patterns and the random noise in that data.

  - When Tom tested his system on historical data that he had already analyzed, he was essentially testing the system against information it was built from, creating an illusion of accuracy. However, lottery numbers are truly random, with each draw being independent of previous draws. There are no patterns that can reliably predict future results.

  - His system failed in practice because the 80% "accuracy" was merely coincidental matching to past data that had already occurred, not a genuine predictive capability for future random events. This demonstrates how easy it is to find false patterns in random data, especially when looking backward.

---

## Question 2: Zoo Animal <a name="question-2"></a>

### 📊 Difficulty

- 👤 Human: 4/5 ⭐⭐⭐⭐
- 🤖 AI: 2/5 ⭐⭐

### ❓ Question

- Consider the following description of an animal at a zoo:

    > This animal is awake and active during the day. It is very playful and likes to explore new things. It often comes close to people who visit. It can figure out how to get treats, and enjoys being with others like itself.

- If we only comparing between the statements below, which of the following statements is the most likely one to be true?
  - a. The animal is a chimpanzee that knows how to use toys.
  - b. The animal is a chimpanzee that likes to be alone.
  - c. The animal is a chimpanzee.
  - d. The animal is a chimpanzee that will happily wait for visitors before the zoo opens.

### ✅ Expected Answer

- c. The animal is a chimpanzee.

  - Because the it has the least assumptions compared to other statements.
  - This is a version of the Linda problem, which is a famous example of the conjunction fallacy.
  - Only [c] is the correct answer, more than one answer is considered incorrect.

---

## Question 3: Revenue Drop <a name="question-3"></a>

### 📊 Difficulty

- 👤 Human: 2/5 ⭐⭐
- 🤖 AI: 3/5 ⭐⭐⭐

### ❓ Question

- The chart below shows the revenue (in millions) of HappyCorp for the year 2019 to current year 2025, when this chart was created.

    ```mermaid
    xychart-beta
        title "Revenue Distribution (2019-2025)"
        x-axis ["2019", "2020", "2021", "2022", "2023", "2024", "2025"]
        y-axis "Revenue (in millions $)" 0 --> 12000
        bar [7732, 2715, 4173, 8224, 8932, 9500, 1518]
    ```

- Why does the revenue for 2025 appear significantly lower compared to previous years? Write your answer below.

### ✅ Expected Answer

- The revenue for 2025 appears significantly lower compared to previous years because 2025 data is not complete yet, as it stated in the question that "the data is up to current year 2025".
- NOTE: Only if the answer mentioned "2025 data is not complete" as one of the plausible reasons, this answer can be considered as correct.
- Any other reasons are not required to be mentioned for the answer to be considered correct, but still welcome as long as they are reasonable and related to the question.

---

## Question 4: Blood Pressure <a name="question-4"></a>

### 📊 Difficulty

- 👤 Human: 3/5 ⭐⭐⭐
- 🤖 AI: 4/5 ⭐⭐⭐⭐

### ❓ Question

- The chart below shows the results of a survey conducted by a medical student on high blood pressure problems. The survey was conducted on ~500 people who works in Hong Kong, grouped by job types.

    ```mermaid
    ---
    config:
        xyChart:
            titleFontSize: 20
            xAxis:
                labelFontSize: 11
    ---
    xychart-beta
        title "High Blood Pressure Problems by Job Type"
        x-axis ["Office Workers", "Healthcare", "Construction ", "Factory Workers", "Retail", "Transport", "Others"]
        y-axis "Number of People" 0 --> 70
        bar [35, 52, 15, 1, 15, 12, 18]
    ```
    
- Based on the chart, what insights can you draw from the data? Write your answer below.

### ✅ Expected Answer

- The chart alone does not offer meaningful insights because it lacks information on the total number of people in each job type, only when we know the total number of people thus the percentage of people in each job type, we can draw meaningful insights. 

  - Extra insights respondents can also provide:
    - "Healthcare workers and office workers having higher survey responses might be due to the connection by alumni or friends of the medical student who conducted the survey."
    - "There are very few factory workers in Hong Kong, which might explain the low number of responses from factory workers."
    - Other insights or information about data bias.

- NOTE: Only if the main point of "lack of percentage information" or "lack of total number of participants in each job type" is provided in the answer, the answer is considered correct, any other insights are just considered as extra insights.

---

## Question 5: Philosophers Logic <a name="question-5"></a>

### 📊 Difficulty

- 👤 Human: 5/5 ⭐⭐⭐⭐⭐
- 🤖 AI: 4/5 ⭐⭐⭐⭐

### ❓ Question

- Consider the following premises:

    ```
    1. All philosophers are poets.
    2. Only some poets are musicians.
    3. All musicians are artists.
    4. No artists are politicians.
    ```
- Which of the following conclusions MUST be true?
  - a. All philosophers are artists.
  - b. There are politicians that are not musicians.
  - c. No poets are politicians.
  - d. There are philosophers that are not politicians.

### ✅ Expected Answer

- b. There are politicians that are not musicians.

    - Drawing a list of all possible venn diagrams based on the premises, we can see that there are politicians that are not musicians and all other statements are not necessarily true.
    - Only [b] is the correct answer, more than one answer is considered incorrect.

---

## Question 6: Number Sequence <a name="question-6"></a>

### 📊 Difficulty

- 👤 Human: 2/5 ⭐⭐
- 🤖 AI: 5/5 ⭐⭐⭐⭐⭐

### ❓ Question

- Consider the following list of integer numbers: [2, 3, 5, 7, 11, 13, 17], based solely on the numbers provided, what MUST be true about the next integer number in the sequence?
  - a. It is greater than 17.
  - b. It is 19.
  - c. It is a prime number.
  - d. It is a number with factor / factors.


### ✅ Expected Answer

- d. It is a number with factor / factors.

    - All integer numbers have at least two factors except the number 1: 1 and the number itself, and 1 also have a single factor of 1.
    - All other answers are not necessarily true, they depend on the assumption that the sequence is following a pattern, which did not state in the question.
    - Only [d] is the correct answer, more than one answer is considered incorrect.

---


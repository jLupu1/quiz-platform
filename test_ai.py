from sentence_transformers import CrossEncoder

model_name = 'cross-encoder/stsb-roberta-base'
print(f"Loading {model_name}... (This might take a few seconds longer than MiniLM)")

# Load the Cross-Encoder model
model = CrossEncoder(model_name)

# --- THE GOLDEN DATASET ---
test_cases = [
    {
        "subject": "Biology (Process)",
        "question": "What is the primary purpose of photosynthesis?",
        "model_answer": "Plants use sunlight, water, and carbon dioxide to create oxygen and energy in the form of sugar.",
        "perfect": "It is how plants make their own food by turning light, water, and CO2 into glucose and releasing oxygen.",
        "partial": "Plants use the sun to make food and oxygen.",
        "bad": "Photosynthesis is when plants use oxygen to create sunlight and water."
    },
    {
        "subject": "History (Cause & Effect)",
        "question": "What was the immediate spark that started World War I?",
        "model_answer": "The assassination of Archduke Franz Ferdinand of Austria in Sarajevo.",
        "perfect": "A Serbian nationalist shot and killed the Austrian Archduke Ferdinand.",
        "partial": "An important leader from Austria was killed.",
        "bad": "Austria invaded Serbia to start the war."
    },
    {
        "subject": "Cybersecurity (Definitions)",
        "question": "What is phishing?",
        "model_answer": "A cyber attack where scammers disguise themselves as a trusted entity to trick victims into revealing sensitive information like passwords.",
        "perfect": "When hackers send fake emails pretending to be a real company so you give them your login details.",
        "partial": "It is a type of scam email to steal your data.",
        "bad": "Phishing is a sport where you catch fish in the ocean."
    }
]

print("\n" + "=" * 50)
print(" AI GRADING ENGINE CALIBRATION TEST (CROSS-ENCODER)")
print("=" * 50)

results = {"perfect": [], "partial": [], "bad": []}

for case in test_cases:
    print(f"\n[{case['subject'].upper()}]")
    print(f"Q: {case['question']}")

    # CROSS-ENCODER LOGIC: We pass the model answer and the student answer together as a pair.
    # The model directly outputs a float score between 0.0 and 1.0.
    score_perfect = float(model.predict([case['model_answer'], case['perfect']]))
    score_partial = float(model.predict([case['model_answer'], case['partial']]))
    score_bad = float(model.predict([case['model_answer'], case['bad']]))

    # Store for averages
    results["perfect"].append(score_perfect)
    results["partial"].append(score_partial)
    results["bad"].append(score_bad)

    print(f"  Perfect Match Score: {score_perfect:.3f}")
    print(f"  Partial Match Score: {score_partial:.3f}")
    print(f"  Tricky Bad Score:    {score_bad:.3f}")

# --- CALCULATE BOUNDARIES ---
print("\n" + "=" * 50)
print(" RECOMMENDED THRESHOLD BOUNDARIES")
print("=" * 50)

min_perfect = min(results["perfect"])
max_partial = max(results["partial"])
max_bad = max(results["bad"])

print(f"1. FULL MARKS Threshold:  Should be around ~{min_perfect - 0.05:.2f} (Lowest Perfect was {min_perfect:.3f})")
print(f"2. ZERO MARKS Threshold:  Should be around ~{max_bad + 0.05:.2f}  (Highest Bad was {max_bad:.3f})")
print(f"3. PARTIAL CREDIT ZONE:   Between {max_bad + 0.05:.2f} and {min_perfect - 0.05:.2f}")
print("=" * 50)
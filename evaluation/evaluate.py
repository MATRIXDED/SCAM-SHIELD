#!/usr/bin/env python3
"""ScamShield Benchmark Evaluation Suite.

Evaluates the ScamShield threat detection engine against a curated dataset
of real-world scam and benign test cases. Computes honest, un-invented
metrics: Accuracy, Precision, Recall, F1 Score, False Positive Rate (FPR),
and False Negative Rate (FNR).
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add backend directory to path so analyze_message can be imported cleanly
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.analyzer import analyze_message


def evaluate(dataset_path: str, threshold: int = 30, verbose: bool = False) -> dict:
    if not os.path.exists(dataset_path):
        print(f"Error: dataset file not found at {dataset_path}", file=sys.stderr)
        sys.exit(1)

    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    total = len(cases)
    if total == 0:
        print("Error: dataset is empty.", file=sys.stderr)
        sys.exit(1)

    tp = 0
    fp = 0
    tn = 0
    fn = 0
    results = []

    print(f"\n========================================================")
    print(f" ScamShield Benchmark Evaluation: {total} Cases (Threshold >= {threshold})")
    print(f"========================================================\n")

    for case in cases:
        cid = case.get("id", "unknown")
        text = case["text"]
        channel = case.get("channel", "sms")
        expected_scam = bool(case["expected_is_scam"])
        category = case.get("category", "General")

        analysis = analyze_message(text=text, metadata={"channel": channel})
        score = analysis.get("risk_score", 0)
        risk_level = analysis.get("risk_level", "UNKNOWN")
        predicted_scam = score >= threshold

        is_correct = predicted_scam == expected_scam

        if expected_scam and predicted_scam:
            tp += 1
            outcome = "TP"
        elif not expected_scam and predicted_scam:
            fp += 1
            outcome = "FP (False Alarm)"
        elif not expected_scam and not predicted_scam:
            tn += 1
            outcome = "TN"
        else:
            fn += 1
            outcome = "FN (Missed Threat)"

        results.append({
            "id": cid,
            "category": category,
            "score": score,
            "risk_level": risk_level,
            "expected_scam": expected_scam,
            "predicted_scam": predicted_scam,
            "outcome": outcome,
            "is_correct": is_correct,
            "warning_signs": analysis.get("warning_signs", [])
        })

        if verbose or not is_correct:
            status_symbol = "PASS" if is_correct else "FAIL"
            print(f"[{status_symbol}] {cid} ({category})")
            print(f"       Expected Scam: {expected_scam} | Predicted: {predicted_scam} | Score: {score} ({risk_level})")
            print(f"       Outcome: {outcome}")
            if not is_correct:
                print(f"       Text: {text[:120]}...")
                print(f"       Signals: {analysis.get('warning_signs', [])}")
            print()

    accuracy = (tp + tn) / total
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    print("--------------------------------------------------------")
    print(f" Performance Metrics Summary ({total}-Case Benchmark Dataset)")
    print("--------------------------------------------------------")
    print(f" Total Evaluated Cases : {total}")
    print(f" True Positives (TP)   : {tp}")
    print(f" True Negatives (TN)   : {tn}")
    print(f" False Positives (FP)  : {fp}")
    print(f" False Negatives (FN)  : {fn}")
    print(f" Dataset Accuracy      : {accuracy:.4f} ({accuracy * 100:.1f}%)")
    print(f" Dataset Precision     : {precision:.4f} ({precision * 100:.1f}%)")
    print(f" Dataset Recall        : {recall:.4f} ({recall * 100:.1f}%)")
    print(f" F1 Score              : {f1:.4f}")
    print(f" False Positive Rate   : {fpr:.4f} ({fpr * 100:.1f}%)")
    print(f" False Negative Rate   : {fnr:.4f} ({fnr * 100:.1f}%)")
    print("--------------------------------------------------------")
    print(" Notice: These metrics reflect evaluation strictly on the")
    print(f" curated {total}-case benchmark dataset and do NOT prove or")
    print(" guarantee generalized real-world accuracy across open-domain")
    print(" threat distributions.")
    print("--------------------------------------------------------\n")

    return {
        "total": total,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fpr,
        "fnr": fnr,
        "results": results
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate ScamShield on benchmark dataset.")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(BASE_DIR / "evaluation" / "benchmark_dataset.json"),
        help="Path to the JSON dataset file"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=30,
        help="Score threshold at or above which a message is classified as scam (default: 30)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed results for every test case"
    )
    parser.add_argument(
        "--min-accuracy",
        type=float,
        default=0.90,
        help="Minimum required accuracy for a successful exit status (default: 0.90)"
    )

    args = parser.parse_args()
    metrics = evaluate(args.dataset, threshold=args.threshold, verbose=args.verbose)

    if metrics["accuracy"] < args.min_accuracy:
        print(f"Evaluation failed: Accuracy {metrics['accuracy']:.2f} is below target {args.min_accuracy:.2f}", file=sys.stderr)
        sys.exit(1)

    print("Benchmark evaluation PASSED successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()

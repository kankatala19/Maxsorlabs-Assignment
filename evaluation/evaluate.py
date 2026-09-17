import json
from pathlib import Path

from backend.llm import decide_ticket


TEST_CASES_FILE = Path(__file__).parent / "test_cases.json"


def evaluate():
    with open(TEST_CASES_FILE, "r", encoding="utf-8") as file:
        test_cases = json.load(file)

    correct = 0

    print("AI Support Ticket Evaluation")
    print("=" * 50)

    for case in test_cases:
        decision = decide_ticket(
            subject=case["message"],
            description=case["message"],
            order_value_inr=case["order_value_inr"],
            days_since_delivery=case["days_since_delivery"],
            days_since_dispatch=case["days_since_dispatch"],
            product_type=case["product_type"],
            opened_status=case["opened_status"],
            order_status=case["order_status"],
        )

        predicted = decision.action.value
        expected = case["expected_action"]

        if predicted == expected:
            correct += 1
            result = "PASS"
        else:
            result = "FAIL"

        print(f"\nCase: {case['case_id']}")
        print(f"Expected : {expected}")
        print(f"Predicted: {predicted}")
        print(f"Result   : {result}")

    total = len(test_cases)
    accuracy = (correct / total) * 100 if total else 0

    print("\n" + "=" * 50)
    print(f"Correct : {correct}/{total}")
    print(f"Accuracy: {accuracy:.2f}%")


if __name__ == "__main__":
    evaluate()
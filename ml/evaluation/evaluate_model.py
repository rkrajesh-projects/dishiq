import os
import sys
import json
import joblib
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from ml.utils.feature_engineering import normalize_text


def evaluate():
    print("=== Evaluating DishIQ Recipe Recommender ===")
    artifacts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "artifacts"))
    joblib_path = os.path.join(artifacts_dir, "recipe_tfidf.joblib")

    if not os.path.exists(joblib_path):
        print("Model artifact not found. Please run training script first.")
        return

    data = joblib.load(joblib_path)
    vectorizer = data["vectorizer"]
    tfidf_matrix = data["tfidf_matrix"]
    recipes = data["recipes"]

    test_queries = [
        "Paneer",
        "Vegetarian fast dinner under 30 mins",
        "Lentil dal soup",
        "Chicken curry",
        "Italian pasta"
    ]

    evaluation_results = []

    for query in test_queries:
        norm_query = normalize_text(query)
        query_vec = vectorizer.transform([norm_query])
        sim_scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

        top_indices = sim_scores.argsort()[::-1][:5]
        top_matches = []
        for idx in top_indices:
            score = float(sim_scores[idx])
            rec = recipes[idx]
            top_matches.append({
                "recipe_name": rec["name"],
                "cuisine": rec["cuisine"],
                "dietary_type": rec["dietary_type"],
                "similarity_score": round(score, 4)
            })

        evaluation_results.append({
            "query": query,
            "top_recommendations": top_matches
        })

    eval_dir = os.path.abspath(os.path.dirname(__file__))
    report_path = os.path.join(eval_dir, "report.json")
    
    with open(report_path, "w") as f:
        json.dump(evaluation_results, f, indent=2)

    print(f"Evaluation report written to {report_path}")
    for res in evaluation_results:
        print(f"\nQuery: '{res['query']}'")
        for r in res["top_recommendations"][:2]:
            print(f"  -> {r['recipe_name']} ({r['dietary_type']}, {r['cuisine']}) - Score: {r['similarity_score']}")


if __name__ == "__main__":
    evaluate()

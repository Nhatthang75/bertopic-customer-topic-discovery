"""Baseline TF-IDF + Logistic Regression cho phân loại flow và phát hiện unknown."""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from bertopic_poc.evaluator import evaluate_fixed_classification, evaluate_unknown_detection, round8


class BaselineClassifier:
    def __init__(self, C: float = 1.0, max_iter: int = 1000):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline

        self.C = C
        self.max_iter = max_iter
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=1.0)),
            ('clf', LogisticRegression(C=C, max_iter=max_iter, random_state=42, solver='lbfgs'))
        ])
        self.classes_: List[str] = []

    def fit(self, texts: List[str], labels: List[str]) -> bool:
        """Fit chỉ trên tập train K."""
        try:
            self.pipeline.fit(texts, labels)
            self.classes_ = list(self.pipeline.named_steps['clf'].classes_)
            return True
        except Exception:
            return False

    def predict_proba(self, texts: List[str]):
        return self.pipeline.predict_proba(texts)

    def predict_with_rejection(
        self,
        texts: List[str],
        q: float
    ) -> Tuple[List[Optional[str]], List[bool], List[float]]:
        """
        Dự đoán với ngưỡng từ chối q:
        - Nếu max_proba < q -> predict = None (abstain), residual_flag = True (unknown)
        - Nếu max_proba >= q -> predict = top class, residual_flag = False
        Trả về (predictions, residual_flags, rejection_scores)
        trong đó rejection_score = 1.0 - max_proba
        """
        probas = self.predict_proba(texts)
        predictions: List[Optional[str]] = []
        residual_flags: List[bool] = []
        rejection_scores: List[float] = []

        for p_row in probas:
            max_p = float(max(p_row))
            top_class = self.classes_[int(p_row.argmax())]
            rejection_score = round8(1.0 - max_p)
            rejection_scores.append(rejection_score)

            if max_p < q:
                predictions.append(None)
                residual_flags.append(True)
            else:
                predictions.append(top_class)
                residual_flags.append(False)

        return predictions, residual_flags, rejection_scores


def search_baseline_grid(
    train_texts: List[str],
    train_labels: List[str],
    dev_texts: List[str],
    dev_labels: List[str],
    known_classes: List[str],
    hidden_dev_class: str = 'shipping_issue',
    c_grid: Tuple[float, ...] = (0.1, 1.0, 10.0),
    q_grid: Tuple[float, ...] = (0.35, 0.50, 0.65, 0.80, 0.95)
) -> Dict:
    """
    Search 15 tổ hợp (C, q) trên Dev K + H_dev:
    Tiêu chí: unknown F1 >= 0.60 rồi maximize known Macro-F1.
    Fallback: harmonic mean của known Macro-F1 và unknown F1 cao nhất, gắn dev_constraint_failed=True.
    Tie-break: unknown F1 cao hơn, rồi C tăng, q tăng.
    """
    results = []
    is_hidden_gt = [label == hidden_dev_class for label in dev_labels]

    for c in c_grid:
        clf = BaselineClassifier(C=c)
        fit_ok = clf.fit(train_texts, train_labels)
        if not fit_ok:
            for q in q_grid:
                results.append({
                    'C': c, 'q': q, 'status': 'convergence_failure',
                    'macro_f1': 0.0, 'unknown_f1': 0.0
                })
            continue

        for q in q_grid:
            preds, residual_flags, rej_scores = clf.predict_with_rejection(dev_texts, q)
            # Evaluate known fixed classification on known samples
            known_idx = [i for i, h in enumerate(is_hidden_gt) if not h]
            known_preds = [preds[i] for i in known_idx]
            known_gt = [dev_labels[i] for i in known_idx]
            fixed_res = evaluate_fixed_classification(known_preds, known_gt, known_classes)

            # Evaluate unknown detection
            unknown_res = evaluate_unknown_detection(residual_flags, is_hidden_gt, rej_scores)

            macro_f1 = fixed_res['macro_f1']
            unknown_f1 = unknown_res['f1']

            results.append({
                'C': c,
                'q': q,
                'status': 'valid',
                'macro_f1': macro_f1,
                'unknown_f1': unknown_f1,
                'harmonic_mean': round8((2 * macro_f1 * unknown_f1) / (macro_f1 + unknown_f1)) if (macro_f1 + unknown_f1) > 0 else 0.0,
                'fixed_metrics': fixed_res,
                'unknown_metrics': unknown_res
            })

    # Selection logic
    qualifying = [r for r in results if r['status'] == 'valid' and r['unknown_f1'] >= 0.60]
    dev_constraint_failed = False

    if qualifying:
        # Maximize known Macro-F1, tie-break: unknown F1 desc, C asc, q asc
        best = sorted(qualifying, key=lambda r: (r['macro_f1'], r['unknown_f1'], -r['C'], -r['q']), reverse=True)[0]
    else:
        # Fallback: harmonic mean, tie-break: unknown F1 desc, C asc, q asc
        valid_res = [r for r in results if r['status'] == 'valid']
        if not valid_res:
            raise ValueError("no_valid_baseline_configuration")
        best = sorted(valid_res, key=lambda r: (r['harmonic_mean'], r['unknown_f1'], -r['C'], -r['q']), reverse=True)[0]
        dev_constraint_failed = True

    return {
        'best_configuration': best,
        'dev_constraint_failed': dev_constraint_failed,
        'all_evaluations': results
    }

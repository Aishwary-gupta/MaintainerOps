import collections
import hashlib
import math
import re
from typing import Dict, List, Set, Tuple
from maintainerops.models.findings import Evidence, Finding, FindingType, Severity
from maintainerops.models.github import IssueItem, PullRequestItem
from maintainerops.rules.base import BaseRule


def _tokenize(text: str) -> List[str]:
    """Tokenize text to lowercase alphanumeric tokens, filtering common stopwords."""
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
        "about", "against", "between", "into", "through", "during", "before", "after",
        "above", "below", "from", "up", "down", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "can", "could",
        "will", "would", "shall", "should", "may", "might", "must", "it", "its", "i",
        "this", "that", "these", "those", "not", "no", "yes", "my", "your", "we", "they"
    }
    words = re.findall(r"\b[a-zA-Z0-9_\-\.]{3,}\b", text.lower())
    return [w for w in words if w not in stop_words]


def _compute_cosine_similarity(tokens_a: List[str], tokens_b: List[str]) -> Tuple[float, List[str]]:
    """Computes exact vector cosine similarity with term frequency and returns shared tokens."""
    if not tokens_a or not tokens_b:
        return 0.0, []

    tf_a = collections.Counter(tokens_a)
    tf_b = collections.Counter(tokens_b)

    common_words = set(tf_a.keys()).intersection(set(tf_b.keys()))
    if not common_words:
        return 0.0, []

    # Dot product
    dot_product = sum(tf_a[w] * tf_b[w] for w in common_words)
    norm_a = math.sqrt(sum(count ** 2 for count in tf_a.values()))
    norm_b = math.sqrt(sum(count ** 2 for count in tf_b.values()))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0, []

    score = dot_product / (norm_a * norm_b)
    # Sort shared words by combined frequency
    sorted_shared = sorted(list(common_words), key=lambda w: tf_a[w] + tf_b[w], reverse=True)
    return score, sorted_shared[:5]


class DuplicateRule(BaseRule):
    """Detects likely duplicate issues using vector similarity and token overlap."""

    def __init__(self, similarity_threshold: float = 0.50):
        self.similarity_threshold = similarity_threshold

    @property
    def name(self) -> str:
        return "duplicate_detection"

    def analyze(
        self, issues: List[IssueItem], pull_requests: List[PullRequestItem]
    ) -> List[Finding]:
        findings: List[Finding] = []
        open_issues = [i for i in issues if not i.is_pull_request]

        if len(open_issues) < 2:
            return findings

        # Double-weight the title by repeating it in token stream
        tokenized_issues = [
            _tokenize(f"{i.title} {i.title} {i.body or ''}") for i in open_issues
        ]

        for idx_a in range(len(open_issues)):
            for idx_b in range(idx_a + 1, len(open_issues)):
                score, common_keywords = _compute_cosine_similarity(
                    tokenized_issues[idx_a], tokenized_issues[idx_b]
                )

                if score >= self.similarity_threshold:
                    item_a = open_issues[idx_a]
                    item_b = open_issues[idx_b]

                    finding_id = hashlib.sha256(
                        f"dup_{min(item_a.number, item_b.number)}_{max(item_a.number, item_b.number)}".encode()
                    ).hexdigest()[:12]

                    findings.append(
                        Finding(
                            id=finding_id,
                            item_type="issue",
                            item_number=item_b.number,
                            item_title=item_b.title,
                            item_url=item_b.html_url,
                            finding_type=FindingType.POSSIBLE_DUPLICATE,
                            severity=Severity.LOW,
                            confidence=round(score, 2),
                            summary=f"Likely duplicate of #{item_a.number} ('{item_a.title}').",
                            evidence=[
                                Evidence(
                                    metric_name="vector_cosine_similarity",
                                    observed_value=round(score, 3),
                                    threshold_value=self.similarity_threshold,
                                    details=f"Cosine similarity score is {round(score, 3)} >= {self.similarity_threshold}.",
                                ),
                                Evidence(
                                    metric_name="shared_keywords",
                                    observed_value=common_keywords,
                                    details=f"Overlapping terms: {', '.join(common_keywords)}",
                                ),
                            ],
                            suggested_action=f"Check if this can be linked or consolidated into #{item_a.number}.",
                            draft_response=f"Hi! This appears related to #{item_a.number}. Please check if the solution discussed there applies.",
                        )
                    )

        return findings

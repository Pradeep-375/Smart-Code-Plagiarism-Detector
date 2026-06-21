from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher
import numpy as np
import re


def compute_cosine_similarity(text1, text2):
    """Compute TF-IDF cosine similarity between two texts."""
    try:
        vectorizer = TfidfVectorizer(
            analyzer='word',
            token_pattern=r'\b\w+\b',
            ngram_range=(1, 2),
            min_df=1
        )
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        return round(float(similarity[0][0]) * 100, 2)
    except:
        return 0.0


def compute_token_similarity(tokens1, tokens2):
    """Compute similarity between token sequences."""
    if not tokens1 or not tokens2:
        return 0.0
    str1 = ' '.join(tokens1)
    str2 = ' '.join(tokens2)
    matcher = SequenceMatcher(None, str1.split(), str2.split())
    return round(matcher.ratio() * 100, 2)


def get_ngrams(tokens, n=3):
    """Generate n-grams from token list."""
    return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


def compute_ngram_similarity(tokens1, tokens2, n=3):
    """Compute Jaccard similarity using n-grams."""
    ngrams1 = set(get_ngrams(tokens1, n))
    ngrams2 = set(get_ngrams(tokens2, n))

    if not ngrams1 or not ngrams2:
        return 0.0

    intersection = ngrams1 & ngrams2
    union = ngrams1 | ngrams2

    return round(len(intersection) / len(union) * 100, 2)


def get_diff_blocks(code1, code2):
    """Get matching and different blocks between two code strings."""
    lines1 = code1.splitlines()
    lines2 = code2.splitlines()

    matcher = SequenceMatcher(None, lines1, lines2)
    matching_blocks = []
    different_blocks = []

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == 'equal':
            matching_blocks.append({
                'lines_a': list(range(i1 + 1, i2 + 1)),
                'lines_b': list(range(j1 + 1, j2 + 1)),
                'content': lines1[i1:i2]
            })
        elif op in ('replace', 'insert', 'delete'):
            different_blocks.append({
                'op': op,
                'lines_a': list(range(i1 + 1, i2 + 1)),
                'lines_b': list(range(j1 + 1, j2 + 1)),
                'content_a': lines1[i1:i2],
                'content_b': lines2[j1:j2]
            })

    return matching_blocks, different_blocks


def classify_plagiarism(score):
    """Classify plagiarism level based on score."""
    if score < 31:
        return 'low', 'Low Similarity', 'success'
    elif score < 61:
        return 'medium', 'Medium Similarity', 'warning'
    else:
        return 'high', 'High Similarity', 'danger'


def compute_final_score(token_sim, ast_sim, structure_sim, logic_sim):
    """Calculate weighted final similarity score."""
    score = (
        token_sim * 0.30 +
        ast_sim * 0.30 +
        structure_sim * 0.20 +
        logic_sim * 0.20
    )
    return round(score, 2)

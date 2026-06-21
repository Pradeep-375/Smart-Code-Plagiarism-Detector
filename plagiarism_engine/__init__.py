from .tokenizer import preprocess_code, detect_language
from .ast_compare import compute_ast_similarity, get_matching_ast_blocks
from .structure_similarity import compute_structure_similarity
from .logic_similarity import (
    compute_cosine_similarity,
    compute_token_similarity,
    compute_ngram_similarity,
    get_diff_blocks,
    classify_plagiarism,
    compute_final_score
)


def analyze_plagiarism(code1, code2, language='python'):
    """
    Full plagiarism analysis pipeline.
    Returns detailed comparison results.
    """
    # Preprocess both files
    proc1 = preprocess_code(code1, language)
    proc2 = preprocess_code(code2, language)

    # Token similarity
    token_sim = compute_token_similarity(proc1['tokens'], proc2['tokens'])

    # Cosine similarity on cleaned code
    cosine_sim = compute_cosine_similarity(proc1['cleaned'], proc2['cleaned'])

    # N-gram similarity
    ngram_sim = compute_ngram_similarity(proc1['tokens'], proc2['tokens'], n=3)

    # AST similarity
    ast_sim = compute_ast_similarity(proc1['cleaned'], proc2['cleaned'], language)

    # Structure similarity
    structure_sim = compute_structure_similarity(proc1['cleaned'], proc2['cleaned'], language)

    # Logic similarity (average of cosine + ngram)
    logic_sim = round((cosine_sim + ngram_sim) / 2, 2)

    # Final weighted score
    final_score = compute_final_score(token_sim, ast_sim, structure_sim, logic_sim)

    # Classify result
    level, level_label, level_color = classify_plagiarism(final_score)

    # Get diff blocks for visualization
    matching_blocks, different_blocks = get_diff_blocks(code1, code2)

    # Get matching AST function blocks
    ast_matches = []
    if language == 'python':
        ast_matches = get_matching_ast_blocks(code1, code2)

    return {
        'final_score': final_score,
        'token_similarity': token_sim,
        'ast_similarity': ast_sim,
        'structure_similarity': structure_sim,
        'logic_similarity': logic_sim,
        'cosine_similarity': cosine_sim,
        'ngram_similarity': ngram_sim,
        'plagiarism_level': level,
        'level_label': level_label,
        'level_color': level_color,
        'matching_blocks': matching_blocks,
        'different_blocks': different_blocks,
        'ast_matches': ast_matches,
        'matching_lines': len([b for b in matching_blocks for _ in b['lines_a']]),
        'total_lines_a': len(code1.splitlines()),
        'total_lines_b': len(code2.splitlines()),
    }

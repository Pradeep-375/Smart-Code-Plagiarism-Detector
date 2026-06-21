import ast
import re
from difflib import SequenceMatcher


def get_python_ast_nodes(code):
    """Extract AST node types from Python code."""
    try:
        tree = ast.parse(code)
        nodes = []
        for node in ast.walk(tree):
            nodes.append(type(node).__name__)
        return nodes
    except SyntaxError:
        return []


def get_generic_ast_nodes(code, language):
    """Extract structural patterns from non-Python code."""
    patterns = {
        'if': r'\bif\s*\(',
        'for': r'\bfor\s*\(',
        'while': r'\bwhile\s*\(',
        'function': r'\b\w+\s+\w+\s*\([^)]*\)\s*\{',
        'class': r'\bclass\s+\w+',
        'return': r'\breturn\b',
        'switch': r'\bswitch\s*\(',
        'try': r'\btry\s*\{',
        'catch': r'\bcatch\s*\(',
    }
    nodes = []
    for name, pattern in patterns.items():
        matches = re.findall(pattern, code, re.MULTILINE)
        nodes.extend([name] * len(matches))
    return nodes


def compute_ast_similarity(code1, code2, language):
    """Compute similarity based on AST node sequences."""
    if language == 'python':
        nodes1 = get_python_ast_nodes(code1)
        nodes2 = get_python_ast_nodes(code2)
    else:
        nodes1 = get_generic_ast_nodes(code1, language)
        nodes2 = get_generic_ast_nodes(code2, language)

    if not nodes1 or not nodes2:
        return 0.0

    seq1 = ' '.join(nodes1)
    seq2 = ' '.join(nodes2)

    matcher = SequenceMatcher(None, seq1.split(), seq2.split())
    return round(matcher.ratio() * 100, 2)


def get_matching_ast_blocks(code1, code2):
    """Find matching AST blocks between two Python files."""
    matching = []
    try:
        tree1 = ast.parse(code1)
        tree2 = ast.parse(code2)

        funcs1 = {node.name: ast.unparse(node)
                  for node in ast.walk(tree1)
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        funcs2 = {node.name: ast.unparse(node)
                  for node in ast.walk(tree2)
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

        for name, body1 in funcs1.items():
            for name2, body2 in funcs2.items():
                ratio = SequenceMatcher(None, body1, body2).ratio()
                if ratio > 0.7:
                    matching.append({
                        'func1': name,
                        'func2': name2,
                        'similarity': round(ratio * 100, 2)
                    })
    except:
        pass
    return matching

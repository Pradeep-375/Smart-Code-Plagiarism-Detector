import re
import ast


def extract_structure_python(code):
    """Extract structural elements from Python code."""
    structure = {
        'functions': [],
        'classes': [],
        'loops': 0,
        'conditions': 0,
        'imports': [],
        'returns': 0,
        'try_except': 0,
    }
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                structure['functions'].append({
                    'name': node.name,
                    'args': len(node.args.args),
                    'lines': node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                })
            elif isinstance(node, ast.ClassDef):
                structure['classes'].append(node.name)
            elif isinstance(node, (ast.For, ast.While)):
                structure['loops'] += 1
            elif isinstance(node, ast.If):
                structure['conditions'] += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                structure['imports'].append(ast.dump(node)[:50])
            elif isinstance(node, ast.Return):
                structure['returns'] += 1
            elif isinstance(node, ast.Try):
                structure['try_except'] += 1
    except:
        pass
    return structure


def extract_structure_generic(code):
    """Extract structural elements from C/Java/C++ code."""
    structure = {
        'functions': [],
        'classes': [],
        'loops': 0,
        'conditions': 0,
        'imports': [],
        'returns': 0,
        'try_except': 0,
    }
    structure['loops'] = len(re.findall(r'\b(for|while|do)\s*[\({]', code))
    structure['conditions'] = len(re.findall(r'\bif\s*\(', code))
    structure['returns'] = len(re.findall(r'\breturn\b', code))
    structure['try_except'] = len(re.findall(r'\btry\s*\{', code))

    # Functions: return_type name(params) {
    funcs = re.findall(r'\b\w+\s+(\w+)\s*\([^)]*\)\s*\{', code)
    structure['functions'] = [{'name': f} for f in funcs]

    # Classes
    classes = re.findall(r'\bclass\s+(\w+)', code)
    structure['classes'] = classes

    # Imports/includes
    imports = re.findall(r'#include\s*[<"][^>"]+[>"]|import\s+[\w.]+;', code)
    structure['imports'] = imports

    return structure


def compute_structure_similarity(code1, code2, language):
    """Compare structural features of two code files."""
    if language == 'python':
        s1 = extract_structure_python(code1)
        s2 = extract_structure_python(code2)
    else:
        s1 = extract_structure_generic(code1)
        s2 = extract_structure_generic(code2)

    scores = []

    # Compare counts (loops, conditions, returns, try_except)
    for key in ['loops', 'conditions', 'returns', 'try_except']:
        v1, v2 = s1[key], s2[key]
        if v1 == 0 and v2 == 0:
            scores.append(1.0)
        elif v1 == 0 or v2 == 0:
            scores.append(0.0)
        else:
            scores.append(min(v1, v2) / max(v1, v2))

    # Compare function count
    fc1, fc2 = len(s1['functions']), len(s2['functions'])
    if fc1 == 0 and fc2 == 0:
        scores.append(1.0)
    elif fc1 == 0 or fc2 == 0:
        scores.append(0.0)
    else:
        scores.append(min(fc1, fc2) / max(fc1, fc2))

    # Compare class count
    cc1, cc2 = len(s1['classes']), len(s2['classes'])
    if cc1 == 0 and cc2 == 0:
        scores.append(1.0)
    elif cc1 == 0 or cc2 == 0:
        scores.append(0.5)
    else:
        scores.append(min(cc1, cc2) / max(cc1, cc2))

    if not scores:
        return 0.0

    return round(sum(scores) / len(scores) * 100, 2)

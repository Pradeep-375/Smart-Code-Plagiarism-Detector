import re
import ast
from pygments import lex
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.token import Token


def detect_language(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    lang_map = {'py': 'python', 'java': 'java', 'c': 'c', 'cpp': 'cpp'}
    return lang_map.get(ext, 'python')


def remove_comments(code, language):
    """Remove comments from source code."""
    if language == 'python':
        # Remove Python comments and docstrings
        code = re.sub(r'#.*', '', code)
        code = re.sub(r'"""[\s\S]*?"""', '', code)
        code = re.sub(r"'''[\s\S]*?'''", '', code)
    elif language in ('java', 'c', 'cpp'):
        # Remove C-style comments
        code = re.sub(r'/\*[\s\S]*?\*/', '', code)
        code = re.sub(r'//.*', '', code)
    return code


def normalize_whitespace(code):
    """Normalize whitespace and blank lines."""
    lines = [line.strip() for line in code.splitlines() if line.strip()]
    return '\n'.join(lines)


def normalize_variables(code, language):
    """Replace variable names with generic placeholders."""
    if language == 'python':
        try:
            tree = ast.parse(code)
            var_map = {}
            counter = [0]

            class VarNormalizer(ast.NodeTransformer):
                def visit_Name(self, node):
                    keywords = {'True', 'False', 'None', 'print', 'range', 'len',
                                'int', 'str', 'float', 'list', 'dict', 'set', 'tuple',
                                'input', 'open', 'type', 'isinstance', 'enumerate'}
                    if node.id not in keywords:
                        if node.id not in var_map:
                            counter[0] += 1
                            var_map[node.id] = f'var{counter[0]}'
                        node.id = var_map[node.id]
                    return node

            VarNormalizer().visit(tree)
            return ast.unparse(tree)
        except:
            pass
    return code


def tokenize_code(code, language):
    """Convert code to token sequence."""
    try:
        lexer = get_lexer_by_name(language)
    except:
        try:
            lexer = guess_lexer(code)
        except:
            return code.split()

    tokens = []
    for token_type, value in lex(code, lexer):
        # Filter meaningful tokens
        if token_type in Token.Comment or token_type in Token.Comment.Single or \
           token_type in Token.Comment.Multiline:
            continue
        if token_type in Token.Text and value.strip() == '':
            continue
        if token_type in Token.Literal.String.Doc:
            continue
        tokens.append(str(token_type))
    return tokens


def preprocess_code(code, language):
    """Full preprocessing pipeline."""
    code = remove_comments(code, language)
    code = normalize_whitespace(code)
    normalized = normalize_variables(code, language)
    tokens = tokenize_code(normalized, language)
    return {
        'cleaned': normalized,
        'tokens': tokens,
        'token_string': ' '.join(tokens)
    }

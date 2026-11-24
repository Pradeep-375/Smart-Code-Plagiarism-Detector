"""Sample programs, mutation helpers and labelled pair generation.

Used by the test-suite, the evaluation script (precision / recall / F1), the optional ML
layer and the demo-data seeder.  Nothing here is executed - the programs are only ever
*read* by the detection engine.
"""
from __future__ import annotations

import ast
import io
import re
import tokenize as pytokenize
from dataclasses import dataclass

from .tokenizer import tokenize

# =========================================================================== Python programs
PY: dict[str, str] = {}

PY["bank_account"] = '''
class BankAccount:
    """Simple bank account with a transaction history."""

    def __init__(self, owner, balance=0):
        self.owner = owner
        self.balance = balance
        self.history = []

    def deposit(self, amount):
        # reject non positive deposits
        if amount <= 0:
            raise ValueError("Deposit must be positive")
        self.balance += amount
        self.history.append(("deposit", amount))
        return self.balance

    def withdraw(self, amount):
        # cannot withdraw more than we have
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount
        self.history.append(("withdraw", amount))
        return self.balance

    def statement(self):
        lines = []
        for kind, amount in self.history:
            lines.append(f"{kind:>10}: {amount:8.2f}")
        lines.append(f"{'balance':>10}: {self.balance:8.2f}")
        return "\\n".join(lines)


def main():
    account = BankAccount("Asha", 100)
    account.deposit(250)
    account.withdraw(75)
    print(account.statement())


if __name__ == "__main__":
    main()
'''

PY["prime_tools"] = '''
import math


def is_prime(n):
    # trial division up to the square root
    if n < 2:
        return False
    for d in range(2, int(math.sqrt(n)) + 1):
        if n % d == 0:
            return False
    return True


def sieve(limit):
    flags = [True] * (limit + 1)
    flags[0] = flags[1] = False
    for i in range(2, int(limit ** 0.5) + 1):
        if flags[i]:
            for j in range(i * i, limit + 1, i):
                flags[j] = False
    return [i for i, ok in enumerate(flags) if ok]


def twin_primes(limit):
    found = sieve(limit)
    pairs = []
    for idx in range(len(found) - 1):
        if found[idx + 1] - found[idx] == 2:
            pairs.append((found[idx], found[idx + 1]))
    return pairs


def main():
    print("Primes below 50:", sieve(50))
    print("Is 97 prime?", is_prime(97))
    print("Twin primes:", twin_primes(60))


main()
'''

PY["grade_report"] = '''
GRADE_BANDS = [(90, "A"), (80, "B"), (70, "C"), (60, "D")]


def letter(score):
    for cutoff, grade in GRADE_BANDS:
        if score >= cutoff:
            return grade
    return "F"


def average(scores):
    if not scores:
        return 0.0
    total = 0
    for s in scores:
        total += s
    return total / len(scores)


def build_report(students):
    report = {}
    for name, marks in students.items():
        avg = average(marks)
        report[name] = {"average": round(avg, 1), "grade": letter(avg), "best": max(marks)}
    return report


def print_report(report):
    print("Student      Avg   Grade  Best")
    for name in sorted(report):
        row = report[name]
        print(f"{name:<10} {row['average']:>6} {row['grade']:>5} {row['best']:>5}")


data = {
    "Ravi": [88, 92, 79],
    "Meena": [95, 91, 98],
    "Karan": [58, 64, 71],
}
print_report(build_report(data))
'''

PY["matrix_ops"] = '''
def make_matrix(rows, cols, fill=0):
    return [[fill for _ in range(cols)] for _ in range(rows)]


def transpose(m):
    result = make_matrix(len(m[0]), len(m))
    for i in range(len(m)):
        for j in range(len(m[0])):
            result[j][i] = m[i][j]
    return result


def multiply(a, b):
    if len(a[0]) != len(b):
        raise ValueError("dimension mismatch")
    out = make_matrix(len(a), len(b[0]))
    for i in range(len(a)):
        for j in range(len(b[0])):
            for k in range(len(b)):
                out[i][j] += a[i][k] * b[k][j]
    return out


def trace(m):
    t = 0
    for i in range(min(len(m), len(m[0]))):
        t += m[i][i]
    return t


A = [[1, 2], [3, 4]]
B = [[0, 1], [1, 0]]
print(multiply(A, B))
print(transpose(A))
print("trace:", trace(A))
'''

PY["word_stats"] = '''
import string


def clean(text):
    table = str.maketrans("", "", string.punctuation)
    return text.lower().translate(table)


def word_counts(text):
    counts = {}
    for word in clean(text).split():
        if word in counts:
            counts[word] += 1
        else:
            counts[word] = 1
    return counts


def longest_word(text):
    best = ""
    for word in clean(text).split():
        if len(word) > len(best):
            best = word
    return best


def top_words(counts, n=3):
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:n]


sample = "The quick brown fox jumps over the lazy dog. The dog barks; the fox runs!"
c = word_counts(sample)
print("unique words:", len(c))
print("longest:", longest_word(sample))
print("top:", top_words(c))
'''

PY["sorting_suite"] = '''
def bubble_sort(values):
    data = list(values)
    n = len(data)
    for i in range(n):
        swapped = False
        for j in range(n - i - 1):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
                swapped = True
        if not swapped:
            break
    return data


def binary_search(sorted_values, target):
    low, high = 0, len(sorted_values) - 1
    while low <= high:
        mid = (low + high) // 2
        if sorted_values[mid] == target:
            return mid
        elif sorted_values[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1


nums = [42, 7, 19, 3, 88, 25]
ordered = bubble_sort(nums)
print(ordered)
print(binary_search(ordered, 19))
print(binary_search(ordered, 100))
'''

PY["linked_stack"] = '''
class Node:
    def __init__(self, value, below=None):
        self.value = value
        self.below = below


class Stack:
    def __init__(self):
        self.top = None
        self.size = 0

    def push(self, value):
        self.top = Node(value, self.top)
        self.size += 1

    def pop(self):
        if self.top is None:
            raise IndexError("pop from empty stack")
        value = self.top.value
        self.top = self.top.below
        self.size -= 1
        return value

    def peek(self):
        return None if self.top is None else self.top.value

    def is_empty(self):
        return self.size == 0


def balanced(expr):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = Stack()
    for ch in expr:
        if ch in "([{":
            stack.push(ch)
        elif ch in pairs:
            if stack.is_empty() or stack.pop() != pairs[ch]:
                return False
    return stack.is_empty()


print(balanced("{[()]}"), balanced("([)]"))
'''

PY["temperature"] = '''
def c_to_f(c):
    return c * 9 / 5 + 32


def f_to_c(f):
    return (f - 32) * 5 / 9


def table(start, stop, step):
    rows = []
    t = start
    while t <= stop:
        rows.append((t, round(c_to_f(t), 1)))
        t += step
    return rows


def describe(readings):
    low = min(readings)
    high = max(readings)
    mean = sum(readings) / len(readings)
    return {"low": low, "high": high, "mean": round(mean, 2)}


for celsius, fahrenheit in table(-10, 40, 10):
    print(f"{celsius:>4}C = {fahrenheit:>6}F")
print(describe([21.5, 19.0, 23.4, 18.2]))
print(round(f_to_c(98.6), 1))
'''

# ---- independent solutions to the SAME tasks (hard negatives: similar purpose, not copied)
PY["prime_alt"] = '''
def check(num):
    if num % 2 == 0:
        return num == 2
    divisor = 3
    while divisor * divisor <= num:
        if num % divisor == 0:
            return False
        divisor += 2
    return num > 1


def first_primes(count):
    primes, candidate = [], 2
    while len(primes) < count:
        if check(candidate):
            primes.append(candidate)
        candidate += 1
    return primes


def gaps(values):
    return [values[i + 1] - values[i] for i in range(len(values) - 1)]


ps = first_primes(12)
print(ps)
print("largest gap:", max(gaps(ps)))
'''

PY["sort_alt"] = '''
def insertion_sort(items):
    result = items[:]
    for pos in range(1, len(result)):
        current = result[pos]
        k = pos - 1
        while k >= 0 and result[k] > current:
            result[k + 1] = result[k]
            k -= 1
        result[k + 1] = current
    return result


def linear_find(items, wanted):
    for index, item in enumerate(items):
        if item == wanted:
            return index
    return None


values = [5, 2, 9, 1, 7]
print(insertion_sort(values))
print(linear_find(values, 9))
'''

PY["words_alt"] = '''
from collections import Counter


def tokens(line):
    return [w.strip(".,;!?").lower() for w in line.split()]


def summary(line):
    freq = Counter(tokens(line))
    most, times = freq.most_common(1)[0]
    return most, times, len(freq)


text = "to be or not to be that is the question"
print(summary(text))
print(sorted(set(tokens(text)), key=len)[-1])
'''

PY_TRAIN = ["bank_account", "prime_tools", "grade_report", "matrix_ops"]
PY_EVAL = ["word_stats", "sorting_suite", "linked_stack", "temperature"]

# ---- hand-written "restructured" variants (same logic, different shape)
PY_RESTRUCTURED: dict[str, str] = {}
PY_RESTRUCTURED["sorting_suite"] = '''
def sort_numbers(values):
    arr = values[:]
    size = len(arr)
    done = False
    end = size - 1
    while not done:
        done = True
        for idx in range(end):
            if arr[idx] > arr[idx + 1]:
                arr[idx], arr[idx + 1] = arr[idx + 1], arr[idx]
                done = False
        end = end - 1
    return arr


def find(sorted_values, target):
    lo = 0
    hi = len(sorted_values) - 1
    while lo <= hi:
        middle = (lo + hi) // 2
        current = sorted_values[middle]
        if current == target:
            return middle
        if current < target:
            lo = middle + 1
        else:
            hi = middle - 1
    return -1


nums = [42, 7, 19, 3, 88, 25]
result = sort_numbers(nums)
print(result)
print(find(result, 19))
print(find(result, 100))
'''
PY_RESTRUCTURED["prime_tools"] = '''
import math


def prime_check(n):
    if n < 2:
        return False
    d = 2
    while d <= math.isqrt(n):
        if n % d == 0:
            return False
        d = d + 1
    return True


def primes_upto(limit):
    marks = [True] * (limit + 1)
    marks[0] = marks[1] = False
    p = 2
    while p * p <= limit:
        if marks[p]:
            for multiple in range(p * p, limit + 1, p):
                marks[multiple] = False
        p = p + 1
    return [n for n in range(limit + 1) if marks[n]]


def twin_pairs(limit):
    ps = primes_upto(limit)
    return [(x, y) for x, y in zip(ps, ps[1:]) if y - x == 2]


print("Primes below 50:", primes_upto(50))
print("Is 97 prime?", prime_check(97))
print("Twin primes:", twin_pairs(60))
'''
PY_RESTRUCTURED["temperature"] = '''
def c_to_f(c):
    return 32 + c * 1.8


def f_to_c(f):
    return (f - 32) / 1.8


def stats(readings):
    total = 0
    for r in readings:
        total = total + r
    return {"low": min(readings), "high": max(readings), "mean": round(total / len(readings), 2)}


def conversion_rows(first, last, step):
    rows = []
    for t in range(first, last + 1, step):
        rows.append((t, round(c_to_f(t), 1)))
    return rows


for celsius, fahrenheit in conversion_rows(-10, 40, 10):
    print(f"{celsius:>4}C = {fahrenheit:>6}F")
print(stats([21.5, 19.0, 23.4, 18.2]))
print(round(f_to_c(98.6), 1))
'''

# =========================================================================== other languages
JAVA: dict[str, str] = {}
JAVA["Inventory"] = '''
import java.util.ArrayList;
import java.util.List;

public class Inventory {
    private final List<String> names = new ArrayList<>();
    private final List<Integer> quantities = new ArrayList<>();

    public void add(String name, int quantity) {
        int index = names.indexOf(name);
        if (index >= 0) {
            quantities.set(index, quantities.get(index) + quantity);
        } else {
            names.add(name);
            quantities.add(quantity);
        }
    }

    public boolean remove(String name, int quantity) {
        int index = names.indexOf(name);
        if (index < 0 || quantities.get(index) < quantity) {
            return false;
        }
        quantities.set(index, quantities.get(index) - quantity);
        return true;
    }

    public int total() {
        int sum = 0;
        for (int q : quantities) {
            sum += q;
        }
        return sum;
    }

    public static void main(String[] args) {
        Inventory inv = new Inventory();
        inv.add("pen", 10);
        inv.add("book", 4);
        inv.remove("pen", 3);
        System.out.println("Total items: " + inv.total());
    }
}
'''
JAVA["ShapeAreas"] = '''
public class ShapeAreas {
    static double circle(double r) {
        return Math.PI * r * r;
    }

    static double rectangle(double w, double h) {
        return w * h;
    }

    static double triangle(double b, double h) {
        return 0.5 * b * h;
    }

    public static void main(String[] args) {
        double[] radii = {1.0, 2.5, 4.0};
        for (int i = 0; i < radii.length; i++) {
            System.out.printf("circle %.1f -> %.2f%n", radii[i], circle(radii[i]));
        }
        System.out.println(rectangle(3, 4) + triangle(6, 2));
    }
}
'''
JAVA_RENAME = {"Inventory": {"names": "labels", "quantities": "counts", "index": "pos", "quantity": "amount",
                             "name": "title", "sum": "acc", "inv": "store", "q": "c", "add": "put",
                             "remove": "take", "total": "grandTotal"},
               "ShapeAreas": {"radii": "rs", "circle": "disc", "rectangle": "box", "triangle": "tri",
                              "r": "rad", "w": "width", "h": "height", "b": "base", "i": "n"}}

C: dict[str, str] = {}
C["array_stats"] = '''
#include <stdio.h>

int maximum(int values[], int count) {
    int best = values[0];
    for (int i = 1; i < count; i++) {
        if (values[i] > best) {
            best = values[i];
        }
    }
    return best;
}

double mean(int values[], int count) {
    long sum = 0;
    for (int i = 0; i < count; i++) {
        sum += values[i];
    }
    return (double) sum / count;
}

void reverse(int values[], int count) {
    for (int lo = 0, hi = count - 1; lo < hi; lo++, hi--) {
        int tmp = values[lo];
        values[lo] = values[hi];
        values[hi] = tmp;
    }
}

int main(void) {
    int data[] = {4, 9, 2, 7, 5};
    int n = 5;
    printf("max=%d mean=%.2f\\n", maximum(data, n), mean(data, n));
    reverse(data, n);
    for (int i = 0; i < n; i++) printf("%d ", data[i]);
    printf("\\n");
    return 0;
}
'''
C["string_utils"] = '''
#include <stdio.h>
#include <string.h>
#include <ctype.h>

int count_vowels(const char *s) {
    int n = 0;
    while (*s) {
        char c = tolower((unsigned char)*s);
        if (c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u') n++;
        s++;
    }
    return n;
}

int is_palindrome(const char *s) {
    int i = 0, j = (int)strlen(s) - 1;
    while (i < j) {
        if (s[i++] != s[j--]) return 0;
    }
    return 1;
}

int main(void) {
    const char *word = "level";
    printf("%d vowels, palindrome=%d\\n", count_vowels(word), is_palindrome(word));
    return 0;
}
'''
C_RENAME = {"array_stats": {"values": "arr", "count": "len", "best": "top", "maximum": "find_max", "mean": "average",
                            "sum": "acc", "reverse": "flip", "lo": "left", "hi": "right", "tmp": "swap",
                            "data": "nums", "n": "size", "i": "k"},
            "string_utils": {"count_vowels": "vowel_total", "is_palindrome": "mirror_ok", "s": "str",
                             "n": "total", "c": "ch", "i": "front", "j": "back", "word": "text"}}

JS: dict[str, str] = {}
JS["cart"] = '''
const TAX_RATE = 0.18;

function subtotal(items) {
  let total = 0;
  for (const item of items) {
    total += item.price * item.qty;
  }
  return total;
}

function applyDiscount(amount, code) {
  const discounts = { SAVE10: 0.1, HALF: 0.5 };
  const rate = discounts[code] || 0;
  return amount - amount * rate;
}

function checkout(items, code) {
  const base = subtotal(items);
  const discounted = applyDiscount(base, code);
  const tax = discounted * TAX_RATE;
  return { base, discounted, tax, total: discounted + tax };
}

const cart = [
  { name: "lamp", price: 40, qty: 2 },
  { name: "desk", price: 150, qty: 1 },
];
console.log(checkout(cart, "SAVE10"));
'''
JS["fizz"] = '''
function fizzbuzz(limit) {
  const out = [];
  for (let n = 1; n <= limit; n++) {
    if (n % 15 === 0) out.push("FizzBuzz");
    else if (n % 3 === 0) out.push("Fizz");
    else if (n % 5 === 0) out.push("Buzz");
    else out.push(String(n));
  }
  return out;
}

const counts = fizzbuzz(30).reduce((acc, word) => {
  acc[word] = (acc[word] || 0) + 1;
  return acc;
}, {});
console.log(counts);
'''
JS_RENAME = {"cart": {"items": "products", "item": "entry", "total": "sum", "amount": "value", "code": "coupon",
                      "discounts": "offers", "rate": "pct", "base": "gross", "discounted": "net", "tax": "levy",
                      "subtotal": "sumItems", "applyDiscount": "reduce", "checkout": "payNow"},
             "fizz": {"limit": "upto", "out": "res", "n": "k", "counts": "tally", "acc": "memo", "word": "w",
                      "fizzbuzz": "game"}}

TS: dict[str, str] = {}
TS["queue"] = '''
interface Job {
  id: number;
  label: string;
}

class JobQueue {
  private items: Job[] = [];

  enqueue(job: Job): void {
    this.items.push(job);
  }

  dequeue(): Job | undefined {
    return this.items.shift();
  }

  get length(): number {
    return this.items.length;
  }
}

const queue = new JobQueue();
queue.enqueue({ id: 1, label: "email" });
queue.enqueue({ id: 2, label: "report" });
const first = queue.dequeue();
console.log(first?.label, queue.length);
'''
TS_RENAME = {"queue": {"items": "buffer", "job": "task", "enqueue": "offer", "dequeue": "poll", "queue": "line",
                       "first": "head", "JobQueue": "TaskLine", "Job": "Task", "label": "title"}}


# =========================================================================== mutation helpers
def _py_comment_spans(src: str) -> list[tuple[int, int]]:
    """Return (line, col) of # comments using the stdlib tokenizer."""
    out = []
    for tok in pytokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == pytokenize.COMMENT:
            out.append(tok.start)
    return out


def reformat_python(src: str) -> str:
    """Normalise layout via ast.unparse (also drops comments)."""
    return ast.unparse(ast.parse(src)) + "\n"


def retab_python(src: str) -> str:
    out = []
    for ln in src.split("\n"):
        stripped = ln.lstrip(" ")
        indent = (len(ln) - len(stripped)) // 4
        out.append("\t" * indent + stripped)
    return "\n".join(out)


def change_comments_python(src: str) -> str:
    texts = ["handle this case first", "helper step", "TODO: double check", "important", "see assignment notes"]
    lines = src.split("\n")
    k = 0
    for (ln, col) in sorted(_py_comment_spans(src), reverse=True):
        line = lines[ln - 1]
        head = line[:col]
        lines[ln - 1] = head + "# " + texts[k % len(texts)]
        k += 1
    # add a few extra comments
    out = []
    for i, line in enumerate(lines):
        out.append(line)
        if line.strip().startswith("for ") and i % 2 == 0:
            indent = line[: len(line) - len(line.lstrip())]
            out.append(indent + "    # iterate through the data")
    return "\n".join(out)


def _py_user_names(src: str) -> list[str]:
    tree = ast.parse(src)
    names: list[str] = []
    for node in ast.walk(tree):
        cand = None
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            cand = node.name
        elif isinstance(node, ast.arg):
            cand = node.arg
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            cand = node.id
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            cand = node.attr
        if cand and cand not in names and not (cand.startswith("__") or cand in ("self", "main", "cls")):
            names.append(cand)
    return names


_SYNONYMS = ["alpha", "beta", "gamma", "delta", "omega", "sigma", "theta", "kappa", "lambda_", "zeta", "eta",
             "rho", "tau", "phi", "chi", "psi", "mu", "nu", "xi", "pi_"]


def rename_identifiers(src: str, language: str, mapping: dict[str, str]) -> str:
    """Replace IDENT tokens (never strings/comments) according to ``mapping``."""
    tr = tokenize(src, language)
    text = src.replace("\r\n", "\n")
    out: list[str] = []
    last = 0
    for t in tr.tokens:
        if t.kind == "IDENT" and t.text in mapping:
            out.append(text[last : t.start])
            out.append(mapping[t.text])
            last = t.end
    out.append(text[last:])
    return "".join(out)


def rename_python(src: str, fraction: float = 1.0, offset: int = 0) -> str:
    names = _py_user_names(src)
    keep = max(1, int(len(names) * fraction))
    mapping = {n: f"{_SYNONYMS[(i + offset) % len(_SYNONYMS)]}{i}" for i, n in enumerate(names[:keep])}
    return rename_identifiers(src, "python", mapping)


def expand_augassign(src: str) -> str:
    return re.sub(r"^(\s*)([A-Za-z_][\w.]*) ([+\-*])= (.+)$", r"\1\2 = \2 \3 \4", src, flags=re.M)


def reorder_python(src: str) -> str:
    """Reverse the order of top-level functions/classes (imports first, script code last)."""
    tree = ast.parse(src)
    lines = src.split("\n")
    imports, defs, rest = [], [], []
    for node in tree.body:
        seg = "\n".join(lines[node.lineno - 1 : node.end_lineno])
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(seg)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defs.append(seg)
        else:
            rest.append(seg)
    return "\n".join(imports) + "\n\n" + "\n\n\n".join(reversed(defs)) + "\n\n\n" + "\n".join(rest) + "\n"


def reformat_brace(src: str, language: str) -> str:
    """Re-render a brace-language program in a different layout (drops comments)."""
    tr = tokenize(src, language)
    out: list[str] = []
    indent = 0
    line: list[str] = []

    def flush() -> None:
        nonlocal line
        if line:
            out.append("  " * indent + " ".join(line))
        line = []

    paren = 0
    for t in tr.tokens:
        if t.text in ("(", "["):
            paren += 1
        elif t.text in (")", "]"):
            paren = max(0, paren - 1)
        if t.text == "{" and paren == 0:
            line.append("{")
            flush()
            indent += 1
        elif t.text == "}" and paren == 0:
            flush()
            indent = max(0, indent - 1)
            out.append("  " * indent + "}")
        elif t.text == ";" and paren == 0:
            line.append(";")
            flush()
        else:
            line.append(t.text)
    flush()
    return "\n".join(out) + "\n"


def change_comments_brace(src: str) -> str:
    out = []
    for i, line in enumerate(src.split("\n")):
        out.append(line)
        if line.rstrip().endswith("{") and i % 2 == 0:
            indent = line[: len(line) - len(line.lstrip())]
            out.append(indent + "  // reviewed: logic unchanged")
    return "\n".join(out)


# =========================================================================== labelled pairs
@dataclass
class LabelledPair:
    name: str
    category: str          # identical|reformatted|renamed|comments|restructured|different|hard_negative
    language: str
    a: str
    b: str
    label: int             # 1 = copied (similarity expected), 0 = independent work


def _python_pairs(names: list[str], include_hard: bool) -> list[LabelledPair]:
    pairs: list[LabelledPair] = []
    for i, n in enumerate(names):
        src = PY[n]
        pairs.append(LabelledPair(f"{n}:identical", "identical", "python", src, src, 1))
        pairs.append(LabelledPair(f"{n}:reformatted", "reformatted", "python", src, reformat_python(src), 1))
        pairs.append(LabelledPair(f"{n}:retabbed", "reformatted", "python", src, retab_python(src), 1))
        pairs.append(LabelledPair(f"{n}:renamed", "renamed", "python", src, rename_python(src, 1.0, i), 1))
        pairs.append(LabelledPair(f"{n}:comments", "comments", "python", src, change_comments_python(src), 1))
        combo = rename_python(expand_augassign(reorder_python(src)), 0.6, i + 3)
        pairs.append(LabelledPair(f"{n}:reorder+rename", "restructured", "python", src, combo, 1))
        other = names[(i + 1) % len(names)]
        pairs.append(LabelledPair(f"{n}~{other}", "different", "python", src, PY[other], 0))
        other2 = names[(i + 2) % len(names)]
        pairs.append(LabelledPair(f"{n}~{other2}", "different", "python", src, PY[other2], 0))
    return pairs


def build_eval_pairs() -> list[LabelledPair]:
    """Held-out evaluation set (programs NOT used for ML training)."""
    pairs = _python_pairs(PY_EVAL, include_hard=True)
    for n, alt in PY_RESTRUCTURED.items():
        pairs.append(LabelledPair(f"{n}:hand-restructured", "restructured", "python", PY[n], alt, 1))
    for n, alt in (("prime_tools", "prime_alt"), ("sorting_suite", "sort_alt"), ("word_stats", "words_alt")):
        pairs.append(LabelledPair(f"{n}~{alt}", "hard_negative", "python", PY[n], PY[alt], 0))
    pairs.append(LabelledPair("prime_alt~sort_alt", "different", "python", PY["prime_alt"], PY["sort_alt"], 0))

    def brace(group: dict[str, str], lang: str, renames: dict[str, dict[str, str]]) -> None:
        keys = list(group)
        for idx, key in enumerate(keys):
            src = group[key]
            pairs.append(LabelledPair(f"{lang}/{key}:identical", "identical", lang, src, src, 1))
            pairs.append(LabelledPair(f"{lang}/{key}:reformatted", "reformatted", lang, src, reformat_brace(src, lang), 1))
            pairs.append(LabelledPair(f"{lang}/{key}:comments", "comments", lang, src, change_comments_brace(src), 1))
            if key in renames:
                pairs.append(LabelledPair(f"{lang}/{key}:renamed", "renamed", lang,
                                          src, rename_identifiers(src, lang, renames[key]), 1))
                pairs.append(LabelledPair(f"{lang}/{key}:rename+reformat", "restructured", lang, src,
                                          reformat_brace(rename_identifiers(src, lang, renames[key]), lang), 1))
            if len(keys) > 1:
                other = keys[(idx + 1) % len(keys)]
                pairs.append(LabelledPair(f"{lang}/{key}~{other}", "different", lang, src, group[other], 0))

    brace(JAVA, "java", JAVA_RENAME)
    brace(C, "c", C_RENAME)
    brace(JS, "javascript", JS_RENAME)
    brace(TS, "typescript", TS_RENAME)
    return pairs


def build_training_pairs() -> list[LabelledPair]:
    """Pairs for the optional ML layer (different base programs than the evaluation set)."""
    pairs = _python_pairs(PY_TRAIN, include_hard=False)
    # extra mutation strengths for variety
    for i, n in enumerate(PY_TRAIN):
        src = PY[n]
        pairs.append(LabelledPair(f"{n}:partial-rename", "renamed", "python", src, rename_python(src, 0.4, i + 7), 1))
        pairs.append(LabelledPair(f"{n}:aug+comments", "comments", "python", src,
                                  change_comments_python(expand_augassign(src)), 1))
    pairs.append(LabelledPair("alt-primes~tools", "hard_negative", "python", PY["prime_tools"], PY["prime_alt"], 0))
    pairs.append(LabelledPair("alt-sort~matrix", "different", "python", PY["sort_alt"], PY["matrix_ops"], 0))
    pairs.append(LabelledPair("alt-words~grades", "different", "python", PY["words_alt"], PY["grade_report"], 0))
    pairs.append(LabelledPair("alt-words~bank", "different", "python", PY["words_alt"], PY["bank_account"], 0))
    return pairs

import random
import re
import math
from dataclasses import dataclass
from typing import Callable, Optional, Union, Protocol

# =========================
# Config / Limites
# =========================

MAX_DICE_QTY = 500
MAX_DICE_SIDES = 1_000_000
MAX_EXPLOSIONS = 10_000


# =========================
# Utilidades
# =========================

def formatar(text: int, wrapper: str) -> str:
    return f"{wrapper}{text}{wrapper}"


def as_int_strict(x: float, ctx: str) -> int:
    if not math.isfinite(x):
        raise ValueError(f"{ctx}: valor inválido")
    r = round(x)
    if abs(x - r) > 1e-9:
        raise ValueError(f"{ctx}: precisa ser inteiro (veio {x})")
    return int(r)


# =========================
# RNG injetável
# =========================

class RandInt(Protocol):
    def __call__(self, a: int, b: int) -> int: ...


# =========================
# Modelo de Rolagem
# =========================

@dataclass
class Roll:
    value: int
    kept: bool = True


@dataclass
class Dice:
    quantity: int
    sides: int
    modifier_text: str = ""

    def text(self) -> str:
        return f"{self.quantity}d{self.sides}{self.modifier_text}"

    def expected(self) -> int:
        return int(self.quantity * (self.sides + 1) / 2)


@dataclass
class RollSet:
    rolls: list[Roll]
    dice: Dice

    def values(self) -> list[int]:
        return [r.value for r in self.rolls]

    def total(self) -> int:
        return sum(r.value for r in self.rolls if r.kept)

    def apply(self, modifier: Callable[["RollSet"], None]):
        modifier(self)
        return self

    def __iter__(self):
        return iter(self.rolls)

    def __repr__(self):
        parts = []
        for r in self.rolls:
            if not r.kept:
                parts.append(formatar(r.value, "~~"))
            elif r.value == self.dice.sides:
                parts.append(formatar(r.value, "**"))
            else:
                parts.append(str(r.value))
        return f"[{', '.join(parts)}] {self.dice.text()}"


# =========================
# Modificadores (efeitos)
# =========================

def keep_highest(n: int):
    def modifier(rs: RollSet):
        n2 = max(0, min(n, len(rs.rolls)))
        ordered = sorted(enumerate(rs.rolls), key=lambda x: x[1].value, reverse=True)
        keep_idx = {i for i, _ in ordered[:n2]}
        for i, r in enumerate(rs.rolls):
            r.kept = i in keep_idx
    return modifier


def keep_lowest(n: int):
    def modifier(rs: RollSet):
        n2 = max(0, min(n, len(rs.rolls)))
        ordered = sorted(enumerate(rs.rolls), key=lambda x: x[1].value)
        keep_idx = {i for i, _ in ordered[:n2]}
        for i, r in enumerate(rs.rolls):
            r.kept = i in keep_idx
    return modifier


def explode(sides: int, randint: RandInt):
    def modifier(rs: RollSet):
        if sides < 2:
            raise ValueError("Explode não pode ser usado em d1")

        explosions = 0
        i = 0
        while i < len(rs.rolls):
            if rs.rolls[i].value == sides:
                explosions += 1
                if explosions > MAX_EXPLOSIONS:
                    raise ValueError("Limite de explosões excedido")
                rs.rolls.append(Roll(randint(1, sides)))
            i += 1
    return modifier


# =========================
# Parser de Modificadores
# =========================

# aceita kh, kl, k, h, l, e, m, x com qualquer número (ou nada)
MODIFIER_PATTERN = re.compile(r"^(kh|kl|k|h|l|e|m|x)(\d*)$")

def parse_modifier(mods: str) -> tuple[str, Optional[int]]:
    if not mods:
        return "", None

    m = MODIFIER_PATTERN.fullmatch(mods)
    if not m:
        raise ValueError(f"Modificador inválido: {mods}")

    kind = m.group(1)
    value_str = m.group(2)
    value = int(value_str) if value_str else 0

    # e, m, x não aceitam número
    if kind in ("e", "m", "x"):
        if value == 0:
            return kind, None
        raise ValueError(f"Esse modificador não aceita número: {kind}{value}")

    # k/h -> kh ; l -> kl
    n = max(value, 1)
    if kind in ("kh", "k", "h"):
        return "kh", n
    if kind in ("kl", "l"):
        return "kl", n

    # não deve chegar aqui
    return kind, n


# =========================
# Operadores / Precedência
# =========================

OPERATORS = {
    "+": (1, lambda a, b: a + b),
    "-": (1, lambda a, b: a - b),
    "*": (2, lambda a, b: a * b),
    "/": (2, lambda a, b: a / b),

    # 'd' precisa ser MAIS forte que postfix para 2d20k -> (2d20)k
    "d": (4, None),

    # unário menos
    "u-": (5, None),
}

# postfix abaixo de 'd'
POSTFIX_MOD_PREC = 3

MOD_TOKEN_REGEX = re.compile(r"(kh|kl|k|h|l|e|m|x)\d*")

TOKEN_REGEX = re.compile(
    r"""
    (\d+)                  |  # número
    (kh|kl|k|h|l|e|m|x)\d*  |  # modificador postfix
    ([+\-*/()d])              # operadores (inclui 'd')
    """,
    re.VERBOSE
)


def is_postfix_mod(token: str) -> bool:
    return bool(MOD_TOKEN_REGEX.fullmatch(token))


def tokenize(expr: str):
    expr = expr.replace(" ", "")
    tokens = []
    prev_kind = None  # None | "value" | "op" | "(" | ")"
    pos = 0

    for m in TOKEN_REGEX.finditer(expr):
        if m.start() != pos:
            raise ValueError(f"Expressão inválida perto de: '{expr[pos:]}'")

        number, mod_head, op = m.groups()
        raw = m.group(0)

        if number:
            tokens.append(int(number))
            prev_kind = "value"
        elif mod_head:
            tokens.append(raw)
            prev_kind = "value"
        else:
            if op == "-" and (prev_kind in (None, "op", "(")):
                tokens.append("u-")
                prev_kind = "op"
            else:
                tokens.append(op)
                prev_kind = "(" if op == "(" else (")" if op == ")" else "op")

        pos = m.end()

    if pos != len(expr):
        raise ValueError(f"Expressão inválida perto de: '{expr[pos:]}'")
    if not tokens:
        raise ValueError("Expressão vazia ou inválida")
    return tokens


def to_rpn(tokens: list):
    output = []
    stack = []

    def prec(tok: str) -> int:
        if tok in OPERATORS:
            return OPERATORS[tok][0]
        if is_postfix_mod(tok):
            return POSTFIX_MOD_PREC
        return -1

    for token in tokens:
        if isinstance(token, int):
            output.append(token)
            continue

        if is_postfix_mod(token):
            # postfix: fica na stack mas respeita precedência
            while stack and (stack[-1] in OPERATORS or is_postfix_mod(stack[-1])) and prec(stack[-1]) >= prec(token):
                output.append(stack.pop())
            stack.append(token)
            continue

        if token == "(":
            stack.append(token)
            continue

        if token == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            if not stack:
                raise ValueError("Parênteses desbalanceados")
            stack.pop()  # remove "("
            # depois de fechar, solta postfix pendente
            while stack and is_postfix_mod(stack[-1]):
                output.append(stack.pop())
            continue

        if token in OPERATORS:
            p = prec(token)
            while stack and (stack[-1] in OPERATORS or is_postfix_mod(stack[-1])) and prec(stack[-1]) >= p:
                output.append(stack.pop())
            stack.append(token)
            continue

        raise ValueError(f"Token desconhecido: {token}")

    while stack:
        if stack[-1] in ("(", ")"):
            raise ValueError("Parênteses desbalanceados")
        output.append(stack.pop())

    return output


# =========================
# AST
# =========================

Value = Union[float, RollSet]

@dataclass
class ExpressionNode:
    value: Optional[int] = None
    left: Optional["ExpressionNode"] = None
    right: Optional["ExpressionNode"] = None
    operator: Optional[str] = None
    cached: Optional[Value] = None


    def eval(self, randint: RandInt) -> Value:
        if self.cached is not None:
            return self.cached

        # folha
        if self.operator is None:
            self.cached = float(self.value)
            return self.cached

        # unário menos
        if self.operator == "u-":
            v = self.left.eval(randint)
            self.cached = -float(v.total() if isinstance(v, RollSet) else v)
            return self.cached

        # postfix mod
        if is_postfix_mod(self.operator):
            base = self.left.eval(randint)
            if not isinstance(base, RollSet):
                raise ValueError(f"Modificador '{self.operator}' só pode ser aplicado em uma rolagem")

            # mantém histórico no texto
            base.dice.modifier_text += self.operator
            kind, val = parse_modifier(self.operator)

            if kind == "m":
                self.cached = float(base.dice.expected())
                return self.cached

            if kind == "x":
                # vira "max": reconstroi RollSet máximo
                d = base.dice
                self.cached = RollSet([Roll(d.sides) for _ in range(d.quantity)], d)
                return self.cached

            if kind == "e":
                base.apply(explode(base.dice.sides, randint))
                self.cached = base
                return self.cached

            if kind == "kh":
                base.apply(keep_highest(val))
                self.cached = base
                return self.cached

            if kind == "kl":
                base.apply(keep_lowest(val))
                self.cached = base
                return self.cached

            raise ValueError(f"Modificador não suportado: {self.operator}")

        # dado
        if self.operator == "d":
            a = self.left.eval(randint)
            b = self.right.eval(randint)

            if isinstance(a, RollSet) or isinstance(b, RollSet):
                raise ValueError("Quantidade/lados não podem ser resultado de rolagem")

            qty = as_int_strict(float(a), "Quantidade de dados")
            sides = as_int_strict(float(b), "Lados do dado")

            if qty < 1 or sides < 1:
                raise ValueError("Dados devem ser maiores que zero")
            if qty > MAX_DICE_QTY:
                raise ValueError(f"Quantidade de dados muito alta (max {MAX_DICE_QTY})")
            if sides > MAX_DICE_SIDES:
                raise ValueError(f"Lados do dado muito alto (max {MAX_DICE_SIDES})")

            dice = Dice(qty, sides)
            self.cached = RollSet([Roll(randint(1, sides)) for _ in range(qty)], dice)
            return self.cached

        # binários normais
        a = self.left.eval(randint)
        b = self.right.eval(randint)

        af = float(a.total()) if isinstance(a, RollSet) else float(a)
        bf = float(b.total()) if isinstance(b, RollSet) else float(b)

        if self.operator == "/" and bf == 0.0:
            raise ValueError("Divisão por zero")

        self.cached = float(OPERATORS[self.operator][1](af, bf))
        return self.cached


    def __repr__(self):
        if self.operator is None:
            return str(self.value)

        if isinstance(self.cached, RollSet):
            return repr(self.cached)

        if self.operator == "u-":
            inner = repr(self.left)
            if self.left.operator:
                inner = f"( {inner} )"
            return f"- {inner}"

        if is_postfix_mod(self.operator):
            inner = repr(self.left)
            if self.left.operator and self.left.operator not in ("d",):
                inner = f"( {inner} )"
            return f"{inner}{self.operator}"

        left = repr(self.left)
        right = repr(self.right)

        my_prec = OPERATORS[self.operator][0]

        if self.left.operator and self.left.operator in OPERATORS:
            if OPERATORS[self.left.operator][0] < my_prec:
                left = f"( {left} )"

        if self.right.operator and self.right.operator in OPERATORS:
            if OPERATORS[self.right.operator][0] < my_prec:
                right = f"( {right} )"

        if self.operator == "d":
            return f"{left}d{right}"

        return f"{left} {self.operator} {right}"


def build_ast(rpn: list) -> ExpressionNode:
    stack: list[ExpressionNode] = []

    for token in rpn:
        if isinstance(token, int):
            stack.append(ExpressionNode(value=token))
            continue

        if token == "u-":
            a = stack.pop()
            stack.append(ExpressionNode(left=a, operator="u-"))
            continue

        if is_postfix_mod(token):
            a = stack.pop()
            stack.append(ExpressionNode(left=a, operator=token))
            continue

        if token in OPERATORS:
            b = stack.pop()
            a = stack.pop()
            stack.append(ExpressionNode(left=a, right=b, operator=token))
            continue

        raise ValueError(f"Token RPN desconhecido: {token}")

    if len(stack) != 1:
        raise ValueError("Expressão malformada")

    return stack[0]


# =========================
# Expressão
# =========================

@dataclass
class Expression:
    root: ExpressionNode
    randint: RandInt

    def total(self) -> int:
        v = self.root.eval(self.randint)
        if isinstance(v, RollSet):
            return v.total()
        return math.floor(float(v))

    def __repr__(self):
        return f"` {self.total()} ` ⟵ {self.root}"


class ExpressionParser:
    @classmethod
    def parse(cls, text: str, randint: RandInt) -> Expression:
        tokens = tokenize(text)
        rpn = to_rpn(tokens)
        ast = build_ast(rpn)
        return Expression(ast, randint)


# =========================
# Interface
# =========================

def roll(text: str, *, seed: Optional[int] = None) -> Expression:
    rng = random.Random(seed) if seed is not None else random
    return ExpressionParser.parse(text, rng.randint)


def test():
    tests = [
        "1d4",
        "2d6",
        "2d6+4",
        "2d4*2",
        "2d20k",
        "3d20k2",
        "4d20kh3",
        "3d20h",
        "5d20l2",
        "(2*3)d12kh1",
        "4d6kh3+2",
    ]
    for i, t in enumerate(tests, 1):
        try:
            print(f"Teste {i} => {roll(t, seed=123)}")
        except Exception as e:
            print(f"Teste {i} => Erro: {e}")


def cli():
    test()
    print("Digite expressões como: 4d6kh3+2 (use seed mudando no código se quiser)")
    while True:
        try:
            i = input("> ")
            print(roll(i))
        except Exception as e:
            print("Erro:", e)


if __name__ == "__main__":
    cli()

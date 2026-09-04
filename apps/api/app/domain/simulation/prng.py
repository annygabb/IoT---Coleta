import math

class DeterministicPRNG:
    """
    Gerador de números pseudoaleatórios determinístico baseado em semente inteira.
    Garante que simulações com a mesma seed gerem exatamente os mesmos resultados (RF-002, DoD-11).
    """
    def __init__(self, seed: int = 20260903):
        self.initial_seed = seed
        self.state = seed

    def reset(self, new_seed: int = None):
        if new_seed is not None:
            self.initial_seed = new_seed
        self.state = self.initial_seed

    def random(self) -> float:
        """Retorna um float no intervalo [0.0, 1.0)"""
        # Linear congruential generator determinístico
        self.state = (self.state * 1664525 + 1013904223) % (2**32)
        return self.state / (2**32)

    def uniform(self, a: float, b: float) -> float:
        """Retorna um float uniforme no intervalo [a, b]"""
        return a + (b - a) * self.random()

    def randint(self, a: int, b: int) -> int:
        """Retorna um inteiro aleatório no intervalo [a, b]"""
        return math.floor(self.uniform(a, b + 1))

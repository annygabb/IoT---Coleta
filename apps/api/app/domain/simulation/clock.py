class SimulationClock:
    """
    Controlador do relógio de simulação desacoplado do tempo de parede (RF-029, RNF-008).
    Permite pausar, retomar e acelerar (1x, 5x, 15x, 30x, 60x, 360x, 1440x).
    """
    def __init__(self, start_seconds: float = 8 * 3600):
        self.sim_time_seconds = start_seconds
        self.sim_day = 1
        self.speed_multiplier = 60.0
        self.is_paused = False

    def tick(self, delta_wall_seconds: float) -> float:
        """Avança o tempo simulado e retorna a quantidade de segundos simulados decorridos."""
        if self.is_paused:
            return 0.0
        delta_sim = delta_wall_seconds * self.speed_multiplier
        self.sim_time_seconds += delta_sim
        if self.sim_time_seconds >= 24 * 3600:
            self.sim_time_seconds -= 24 * 3600
            self.sim_day += 1
        return delta_sim

    def get_time_string(self) -> str:
        h = int((self.sim_time_seconds // 3600) % 24)
        m = int((self.sim_time_seconds // 60) % 60)
        s = int(self.sim_time_seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def get_iso_sim_time(self) -> str:
        # Exemplo formatado: 2026-09-03T08:00:00-03:00
        day_str = f"{self.sim_day:02d}"
        time_str = self.get_time_string()
        return f"2026-09-{day_str}T{time_str}-03:00"

    def set_speed(self, speed: float):
        self.speed_multiplier = max(0.0, speed)

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

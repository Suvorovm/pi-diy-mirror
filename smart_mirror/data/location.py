from dataclasses import dataclass, field


@dataclass
class LocationData:
    latitude: float
    longitude: float
    city: str = ""

    def __str__(self) -> str:
        if self.city:
            return f"{self.city} ({self.latitude:.4f}, {self.longitude:.4f})"
        return f"{self.latitude:.4f}, {self.longitude:.4f}"

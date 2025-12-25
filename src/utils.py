import pandas as pd

from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from workalendar.europe import Russia

import config

def geocode_address(address: str):
    """Преобразует адрес в координаты (lat, lon)."""
    geo = Nominatim(user_agent="geoplanning")
    loc = geo.geocode(address)
    return loc.latitude, loc.longitude


def validate_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    Проверяет входные данные.
    """
    required = ['point_id', 'latitude', 'longitude', 'visits_per_month']
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Отсутствуют обязательные столбцы: {missing}")

    df = df.dropna(subset=['latitude', 'longitude'])
    df = df[(df.latitude.between(-90, 90)) & (df.longitude.between(-180, 180))]
    df = df[df.visits_per_month > 0]

    if 'service_time_min' not in df.columns:
        df['service_time_min'] = config.DEFAULT_SERVICE_TIME_MIN
    else:
        df['service_time_min'] = df['service_time_min'].fillna(config.DEFAULT_SERVICE_TIME_MIN)

    return df


def calculate_distance(p1, p2) -> float:
    """Расстояние между двумя точками в километрах."""
    return geodesic(p1, p2).km


def get_working_days(year: int, month: int):
    """Список рабочих дней месяца (5/2, РФ)."""
    cal = Russia()
    days = pd.date_range(f"{year}-{month}-01", f"{year}-{month}-28")
    return [d for d in days if cal.is_working_day(d)]


def yandex_route_link(coords):
    """Ссылка на маршрут в Яндекс Картах."""
    points = "~".join([f"{lat},{lon}" for lat, lon in coords])
    return f"https://yandex.ru/maps/?rtext={points}&rtt=auto"
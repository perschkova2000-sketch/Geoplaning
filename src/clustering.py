import pandas as pd
import numpy as np

from sklearn.cluster import KMeans

def expand_visits_flat(df: pd.DataFrame) -> pd.DataFrame:
    """
    Разворачивает visits_per_month в плоский список визитов
    БЕЗ привязки к датам.
    """
    rows = []

    for _, r in df.iterrows():
        for _ in range(int(r.visits_per_month)):
            rows.append({
                'point_id': r.point_id,
                'manager_id': r.manager_id,
                'latitude': r.latitude,
                'longitude': r.longitude,
                'service_time_min': r.service_time_min
            })

    return pd.DataFrame(rows)

def assign_visits_to_days(
    visits: pd.DataFrame,
    work_days: list,
    max_points_per_day: int
):
    """
    Формирует реальный календарь:
    - 1 менеджер
    - 1 день
    - ≤ max_points_per_day
    Возвращает:
    - schedule (что обслуживаем)
    - unserved (что не влезло в месяц)
    """
    schedule_rows = []
    unserved_rows = []

    for manager_id, grp in visits.groupby('manager_id'):
        # Можно отсортировать — например, по расстоянию от офиса
        grp = grp.reset_index(drop=True)

        day_idx = 0

        for i in range(0, len(grp), max_points_per_day):
            chunk = grp.iloc[i:i + max_points_per_day]

            if day_idx >= len(work_days):
                unserved_rows.append(chunk)
            else:
                day = work_days[day_idx]
                for _, r in chunk.iterrows():
                    schedule_rows.append({
                        'point_id': r.point_id,
                        'manager_id': manager_id,
                        'visit_day': day,
                        'latitude': r.latitude,
                        'longitude': r.longitude,
                        'service_time_min': r.service_time_min
                    })
                day_idx += 1

    schedule = pd.DataFrame(schedule_rows)
    unserved = (
        pd.concat(unserved_rows)
        if unserved_rows else
        pd.DataFrame(columns=visits.columns)
    )

    return schedule, unserved


def cluster_points(points: pd.DataFrame, max_points: int, random_state: int = 42):
    """
    Кластеризация точек одного дня.
    Размер кластера не превышает max_points.
    """
    if len(points) <= max_points:
        points['cluster_id'] = 0
        return points

    n_clusters = int(np.ceil(len(points) / max_points))
    model = KMeans(n_clusters=n_clusters, random_state=random_state)
    points = points.copy()
    points['cluster_id'] = model.fit_predict(points[['latitude', 'longitude']])
    return points

def assign_managers(df: pd.DataFrame, n_managers: int, random_state: int = 42):
    """
    Закрепляет точки за менеджерами на основе географии.
    Используется KMeans по координатам.
    """
    model = KMeans(n_clusters=n_managers, random_state=random_state)
    df = df.copy()
    df['manager_id'] = model.fit_predict(df[['latitude', 'longitude']]) + 1
    return df
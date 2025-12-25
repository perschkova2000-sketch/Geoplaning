import pandas as pd
import numpy as np

from geopy.distance import geodesic

import config
import utils
import clustering
import routing
import visualize

# Загрузка данных
df_raw = pd.read_csv(config.DATA_PATH)
df = utils.validate_points(df_raw)

# Назначаем менеджеров
df = clustering.assign_managers(df, config.N_MANAGERS, config.RANDOM_SEED)

# Офис
office_lat, office_lon = utils.geocode_address(config.OFFICE_ADDRESS)
office = (office_lat, office_lon)

# Рабочие дни
work_days = utils.get_working_days(config.YEAR, config.MONTH)

# Разворачивание посещений
visits_flat = clustering.expand_visits_flat(df)

schedule_base, unserved = clustering.assign_visits_to_days(
    visits_flat,
    work_days,
    config.MAX_POINTS_PER_DAY
)

# Кластеризация + маршрутизация
result = []
for (manager_id, day), group in schedule_base.groupby(['manager_id', 'visit_day']):
    clustered = clustering.cluster_points(group, config.MAX_POINTS_PER_DAY, config.RANDOM_SEED)
    for cluster_id, cl in clustered.groupby('cluster_id'):
        routed = routing.build_route(cl, office)
        routed['manager_id'] = manager_id
        routed['visit_day'] = day
        routed['cluster_id'] = cluster_id
        result.append(routed)

schedule = pd.concat(result)

# Лист 1: детальный план
sheet1 = schedule[['point_id', 'visit_day', 'manager_id', 'cluster_id', 'order_in_route']]

# Лист 2: план по дням    
summary = []
for (day, manager), grp in schedule.groupby(['visit_day', 'manager_id']):
    coords = [office] + [
        (df[df.point_id == pid].latitude.values[0],
         df[df.point_id == pid].longitude.values[0])
        for pid in grp.sort_values('order_in_route').point_id
    ] + [office]

    travel_sec = routing.osrm_route_duration(coords)

    service_min = df[df.point_id.isin(grp.point_id)].service_time_min.sum()

    if travel_sec is None:
        travel_min = np.nan
    else:
        travel_min = travel_sec / 60
    total_time = travel_min + service_min if not np.isnan(travel_min) else np.nan
    

    summary.append({
        'date': day,
        'manager_id': manager,
        'points': ', '.join(map(str, grp.point_id.tolist())),
        'points_count': len(grp),
        'total_time_min': round(travel_min + service_min, 1),
        'yandex_route': utils.yandex_route_link(coords)
    })

sheet2 = pd.DataFrame(summary)

# Лист 3: необслуженные точки
served = set(schedule.point_id)

unserved = (
    df[~df.point_id.isin(served)]
    .loc[:, ['point_id', 'manager_id', 'latitude', 'longitude']]
    .copy()
)

unserved['dist_from_office_km'] = [
    geodesic(office, (lat, lon)).km
    for lat, lon in zip(unserved['latitude'].values, unserved['longitude'].values)
]

unserved = unserved.sort_values('dist_from_office_km', ascending=False)

with pd.ExcelWriter("routes_result.xlsx", engine="xlsxwriter") as writer:
    sheet1.to_excel(writer, sheet_name="Детальный план", index=False)
    sheet2.to_excel(writer, sheet_name="План по дням", index=False)
    unserved.to_excel(writer, sheet_name="Необслуженные точки", index=False)
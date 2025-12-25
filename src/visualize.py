import folium

def visualize_day(schedule_df, points_df, office_coord, selected_day):
    """Визуализация маршрутов всех менеджеров за выбранный день."""
    day_df = schedule_df[schedule_df.visit_day == selected_day]

    m = folium.Map(location=office_coord, zoom_start=11)
    folium.Marker(
        office_coord,
        icon=folium.Icon(color='red', icon='home'),
        popup='Офис'
    ).add_to(m)

    colors = {1: 'blue', 2: 'green', 3: 'purple'}

    for manager_id, group in day_df.groupby('manager_id'):
        color = colors.get(manager_id, 'gray')
        coords = [office_coord]

        for _, r in group.sort_values('order_in_route').iterrows():
            p = points_df[points_df.point_id == r.point_id].iloc[0]
            coords.append((p.latitude, p.longitude))
            folium.CircleMarker(
                [p.latitude, p.longitude],
                radius=5,
                color=color,
                fill=True,
                popup=f"Менеджер {manager_id}, точка {r.point_id}"
            ).add_to(m)

        coords.append(office_coord)
        folium.PolyLine(coords, color=color).add_to(m)

    return m
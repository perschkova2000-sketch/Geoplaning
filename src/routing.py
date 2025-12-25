import pandas as pd
import requests
import time

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

def osrm_route_duration(coords, sleep_sec=0.5):
    """
    Возвращает длительность маршрута в секундах.
    При ошибке возвращает None.
    """
    if len(coords) < 2:
        return 0

    coord_str = ';'.join([f"{lon},{lat}" for lat, lon in coords])
    url = f"http://router.project-osrm.org/route/v1/driving/{coord_str}"
    params = {"overview": "false"}

    try:
        r = requests.get(url, params=params, timeout=10)

        # если сервер ответил не 200
        if r.status_code != 200:
            return None

        data = r.json()

        if 'routes' not in data or not data['routes']:
            return None

        time.sleep(sleep_sec)  # защита от rate limit
        return data['routes'][0]['duration']

    except Exception:
        return None


def build_route(points: pd.DataFrame, office_coord):
    """
    Строит маршрут внутри кластера (TSP).
    Возвращает точки с order_in_route.
    """
    if len(points) == 1:
        points = points.copy()
        points['order_in_route'] = 1
        return points

    coords = [office_coord] + list(zip(points.latitude, points.longitude))
    coord_str = ';'.join([f"{lon},{lat}" for lat, lon in coords])
    url = f"http://router.project-osrm.org/table/v1/driving/{coord_str}?annotations=duration"
    matrix = requests.get(url).json()['durations']

    manager = pywrapcp.RoutingIndexManager(len(coords), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def time_cb(i, j):
        return int(matrix[manager.IndexToNode(i)][manager.IndexToNode(j)])

    transit_cb = routing.RegisterTransitCallback(time_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)

    search = pywrapcp.DefaultRoutingSearchParameters()
    search.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

    solution = routing.SolveWithParameters(search)

    if solution is None:
        points['order_in_route'] = None
        return points

    order = []
    idx = routing.Start(0)
    while not routing.IsEnd(idx):
        node = manager.IndexToNode(idx)
        if node != 0:
            order.append(node - 1)
        idx = solution.Value(routing.NextVar(idx))

    ordered = points.iloc[order].copy()
    ordered['order_in_route'] = range(1, len(ordered) + 1)
    return ordered
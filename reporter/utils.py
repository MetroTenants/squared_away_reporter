import json
import os
from datetime import date, datetime, timedelta

from flask import g
from shapely.geometry import Point, shape
from sqlalchemy import union_all
from sqlalchemy.dialects.postgresql import array_agg

from .database import db_session as session
from .models import Addresses, Calls, Categories, Issues
from .pyrtree import Rect, RTree


def zip_rtree():
    current_dir = os.path.dirname(__file__)
    geo_path = os.path.join(current_dir, "static", "js", "chi_zips.geojson")
    with open(geo_path, "r") as gf:
        chi_zips = json.load(gf)
    tree = RTree()
    for i, a in enumerate(chi_zips["features"]):
        shp = shape(a["geometry"])
        tree.insert({"idx": i, "shape": shp}, Rect(*shp.bounds))
    return chi_zips, tree


def ward_rtree():
    current_dir = os.path.dirname(__file__)
    geo_path = os.path.join(current_dir, "static", "js", "chi_wards.geojson")
    with open(geo_path, "r") as gf:
        chi_wards = json.load(gf)
    tree = RTree()
    for i, a in enumerate(chi_wards["features"]):
        shp = shape(a["geometry"])
        tree.insert(
            {"idx": i, "shape": shp, "ward": a["properties"]["ward"]}, Rect(*shp.bounds)
        )
    return chi_wards, tree


def load_rtree(geog):
    geog_tree = f"{geog}_tree"
    geog_func = zip_rtree if geog == "zips" else ward_rtree
    if geog_tree not in g:
        setattr(g, geog_tree, geog_func())
    return getattr(g, geog_tree)


def handle_dates(start_date, end_date):
    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start_date = date.today() - timedelta(days=365)
    if end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end_date = date.today()

    return start_date, end_date


def call_issue_geog_query(cls, start_date, end_date, categories, zip_codes):
    filter_list = [cls.created_at >= start_date, cls.created_at <= end_date]
    if categories:
        filter_list.append(Categories.name.in_(categories.split(",")))
    if zip_codes:
        filter_list.append(Addresses.zip.in_(zip_codes.split(",")))

    return (
        session.query(
            array_agg(Categories.name).label("categories"),
            cls.id.label("id"),
            cls.created_at.label("created_at"),
            Addresses.lat.label("lat"),
            Addresses.lon.label("lon"),
        )
        .outerjoin(cls.categories, Addresses)
        .filter(*filter_list)
        .order_by(cls.created_at.desc())
        .group_by(cls.id, cls.created_at, Addresses)
        .distinct(cls.id, cls.created_at)
    )


def handle_geog_filter(request, start_date, end_date):
    categories = request.args.get("categories")
    zip_codes = request.args.get("zip_codes")
    geog = request.args.get("geog", "wards")

    combined_query = union_all(
        call_issue_geog_query(Calls, start_date, end_date, categories, zip_codes),
        call_issue_geog_query(Issues, start_date, end_date, categories, zip_codes),
    ).alias("call_issues")

    chi_areas, tree = load_rtree(geog)

    for p in session.query(combined_query):
        if p.lon is None or p.lat is None:
            continue
        for r in tree.query_point((p.lon, p.lat)):
            if not r.leaf_obj():
                continue
            shp = r.leaf_obj()
            pt = Point(p.lon, p.lat)
            if pt.within(shp["shape"]):
                props = chi_areas["features"][shp["idx"]]["properties"]
                if "ci_count" not in props:
                    chi_areas["features"][shp["idx"]]["properties"]["ci_count"] = 0
                chi_areas["features"][shp["idx"]]["properties"]["ci_count"] += 1

    return chi_areas

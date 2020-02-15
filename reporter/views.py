from collections import defaultdict
from datetime import date

from flask import Blueprint, jsonify, render_template, request, send_file
from flask_login import login_required
from shapely.geometry import Point
from sqlalchemy import union_all
from sqlalchemy.orm import aliased, contains_eager, subqueryload

from .auth import admin_required
from .database import db_session as session
from .export import CSV_COLS, EVICTION_COLS, CsvExport, EvictionRecordRow, RecordRow
from .models import Addresses, Calls, Categories, EvictionRecords, Issues, User
from .utils import call_issue_geog_query, handle_dates, handle_geog_filter, load_rtree

views = Blueprint("views", __name__)


@views.route("/filter-geo")
@login_required
def filter_geo():
    start_date, end_date = handle_dates(
        request.args.get("start_date"), request.args.get("end_date")
    )
    return jsonify(handle_geog_filter(request, start_date, end_date))


@views.route("/filter-csv")
@login_required
def filter_csv():
    start_date, end_date = handle_dates(
        request.args.get("start_date"), request.args.get("end_date")
    )
    chi_areas = handle_geog_filter(request, start_date, end_date)

    geog = request.args.get("geog", "wards")
    categories = request.args.get("categories")

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    filename = "sa_export_{}_{}_{}.csv".format(start_date_str, end_date_str, geog)

    geog_name = geog[:-1]
    export = CsvExport(
        [geog_name, "ci_count", start_date_str, end_date_str, categories, geog],
        [
            [feat["properties"][geog_name], feat["properties"].get("ci_count", 0)]
            for feat in chi_areas["features"]
        ],
    )

    return send_file(
        export.write_rows(),
        mimetype="text/csv",
        as_attachment=True,
        attachment_filename=filename,
    )


@views.route("/detail-csv")
@login_required
def detail_csv():
    categories = request.args.get("categories")
    zip_codes = request.args.get("zip_codes")
    start_date, end_date = handle_dates(
        request.args.get("start_date"), request.args.get("end_date")
    )
    in_chicago = request.args.get("outside_chicago") is None

    filter_list = []
    if categories:
        filter_list.append(Categories.name.in_(categories.split(",")))
    if zip_codes:
        filter_list.append(Addresses.zip.in_(zip_codes.split(",")))

    tenant_alias = aliased(User)
    landlord_alias = aliased(User)
    rep_alias = aliased(User)

    call_query = (
        session.query(Calls)
        .outerjoin(Calls.address)
        .outerjoin(tenant_alias, Calls.tenant)
        .outerjoin(landlord_alias, Calls.landlord)
        .outerjoin(rep_alias, Calls.rep)
        .outerjoin(Calls.categories)
        .options(
            contains_eager(Calls.address),
            contains_eager(Calls.tenant, alias=tenant_alias),
            contains_eager(Calls.landlord, alias=landlord_alias),
            contains_eager(Calls.rep, alias=rep_alias),
        )
        .filter(
            Calls.created_at >= start_date, Calls.created_at <= end_date, *filter_list
        )
        .order_by(Calls.created_at.asc())
    )

    issue_query = (
        session.query(Issues)
        .outerjoin(Issues.address)
        .outerjoin(tenant_alias, Issues.tenant)
        .outerjoin(landlord_alias, Issues.landlord)
        .outerjoin(Issues.categories)
        .options(
            contains_eager(Issues.address),
            contains_eager(Issues.tenant, alias=tenant_alias),
            contains_eager(Issues.landlord, alias=landlord_alias),
        )
        .filter(
            Issues.created_at >= start_date, Issues.created_at <= end_date, *filter_list
        )
        .order_by(Issues.created_at.asc())
    )

    calls = [RecordRow(c) for c in call_query]
    issues = [RecordRow(i) for i in issue_query]
    calls_issues = calls + issues

    if in_chicago:
        chi_wards, tree = load_rtree("wards")

        for record in calls_issues:
            if record.lon is None or record.lat is None:
                continue
            for r in tree.query_point((record.lon, record.lat)):
                if not r.leaf_obj:
                    continue
                shp = r.leaf_obj()
                if shp is None:
                    continue
                pt = Point(record.lon, record.lat)
                if pt.within(shp["shape"]):
                    record.ward = shp["ward"]

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    filename = "sa_export_detail_{}_{}.csv".format(start_date_str, end_date_str)

    export = CsvExport(CSV_COLS, [r.as_list() for r in calls_issues])
    return send_file(
        export.write_rows(),
        mimetype="text/csv",
        as_attachment=True,
        attachment_filename=filename,
    )


@views.route("/eviction-record-csv")
@admin_required
def eviction_record_detail_csv():
    start_date, end_date = handle_dates(
        request.args.get("start_date"), request.args.get("end_date")
    )

    tenant_alias = aliased(User)
    landlord_alias = aliased(User)
    rep_alias = aliased(User)

    record_query = (
        session.query(EvictionRecords)
        .outerjoin(EvictionRecords.calls)
        .outerjoin(Calls.address)
        .outerjoin(tenant_alias, Calls.tenant)
        .outerjoin(landlord_alias, Calls.landlord)
        .outerjoin(rep_alias, Calls.rep)
        .options(
            subqueryload(EvictionRecords.calls),
            subqueryload(EvictionRecords.calls).joinedload(Calls.address),
            subqueryload(EvictionRecords.calls).joinedload(Calls.tenant),
            subqueryload(EvictionRecords.calls).joinedload(Calls.landlord),
            subqueryload(EvictionRecords.calls).joinedload(Calls.rep),
            subqueryload(EvictionRecords.calls).joinedload(Calls.categories),
            contains_eager(EvictionRecords.calls).contains_eager(Calls.address),
            contains_eager(EvictionRecords.calls).contains_eager(
                Calls.tenant, alias=tenant_alias
            ),
            contains_eager(EvictionRecords.calls).contains_eager(
                Calls.landlord, alias=landlord_alias
            ),
            contains_eager(EvictionRecords.calls).contains_eager(
                Calls.rep, alias=rep_alias
            ),
        )
        .filter(
            EvictionRecords.created_at >= start_date,
            EvictionRecords.created_at <= end_date,
        )
        .order_by(EvictionRecords.created_at.asc())
        .all()
    )
    records = [EvictionRecordRow(r) for r in record_query]

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    filename = "sa_export_evictions_{}_{}.csv".format(start_date_str, end_date_str)
    export = CsvExport(
        EVICTION_COLS + [f"call_{col}" for col in CSV_COLS],
        [r.as_list() for r in records],
    )

    return send_file(
        export.write_rows(),
        mimetype="text/csv",
        as_attachment=True,
        attachment_filename=filename,
    )


@views.route("/")
@login_required
def index():
    return render_template("index.html")


@views.route("/breakdown-wards")
@login_required
def breakdown_wards():
    start_date, end_date = handle_dates(
        request.args.get("start_date"), request.args.get("end_date")
    )
    categories = request.args.get("categories")

    filter_list = []
    if categories:
        filter_list.append(Categories.name.in_(categories.split(",")))

    combined_query = union_all(
        call_issue_geog_query(Calls, start_date, end_date, categories, None),
        call_issue_geog_query(Issues, start_date, end_date, categories, None),
    ).alias("call_issues")

    chi_wards, tree = load_rtree("wards")

    ward_dict = {str(i): defaultdict(lambda: 0) for i in range(1, 51)}
    for p in session.query(combined_query):
        if p.lon is None or p.lat is None:
            continue
        for r in tree.query_point((p.lon, p.lat)):
            if not r.leaf_obj():
                continue
            shp = r.leaf_obj()
            pt = Point(p.lon, p.lat)
            if pt.within(shp["shape"]):
                ward = chi_wards["features"][shp["idx"]]["properties"]["ward"]
                for c in p.categories:
                    if c is not None:
                        ward_dict[ward][c] += 1

    return jsonify(ward_dict)


@views.route("/breakdown")
@login_required
def breakdown():
    return render_template("breakdown.html", today=date.today())


@views.route("/print")
@login_required
def print_view():
    start_date, end_date = handle_dates(
        request.args.get("start_date"), request.args.get("end_date")
    )
    chi_areas = handle_geog_filter(request, start_date, end_date)

    # Handle report titles based on year and month
    if start_date.year == end_date.year:
        # If basic annual report, just return year
        if start_date.month == 1 and end_date.month == 12:
            report_time = start_date.year
        # If in same year, return Mon-Mon YYYY
        else:
            report_time = "{}-{} {}".format(
                start_date.strftime("%b"), end_date.strftime("%b"), start_date.year
            )
    # If not same year, return Mon YYYY-Mon YYYY
    else:
        report_time = "{} {}-{} {}".format(
            start_date.strftime("%b"),
            start_date.year,
            end_date.strftime("%b"),
            end_date.year,
        )
    if request.args.get("report_title"):
        report_title = request.args.get("report_title")
    else:
        report_title = "Calls and Issues: {}".format(report_time)

    return render_template(
        "print.html",
        geo_dump=chi_areas,
        report_title=report_title,
        colors=request.args.get("color_choice", "YlOrBr"),
        today=date.today(),
    )

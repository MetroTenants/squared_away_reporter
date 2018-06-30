import csv
import json
import os
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO

from flask import Blueprint, g, jsonify, render_template, request, send_file
from flask_login import login_required
from shapely.geometry import Point, shape
from sqlalchemy import union_all
from sqlalchemy.dialects.postgresql import array_agg
from sqlalchemy.orm import joinedload, subqueryload

from .database import db_session as session
from .export import CSV_COLS, RecordRow
from .models import Addresses, Calls, Categories, Issues
from .pyrtree import Rect, RTree

views = Blueprint('views', __name__)


def zip_rtree():
    current_dir = os.path.dirname(__file__)
    geo_path = os.path.join(current_dir, 'static', 'js', 'chi_zips.geojson')
    with open(geo_path, 'r') as gf:
        chi_zips = json.load(gf)
    tree = RTree()
    for i, a in enumerate(chi_zips['features']):
        shp = shape(a['geometry'])
        tree.insert({'idx': i, 'shape': shp}, Rect(*shp.bounds))
    return chi_zips, tree


def ward_rtree():
    current_dir = os.path.dirname(__file__)
    geo_path = os.path.join(current_dir, 'static', 'js', 'chi_wards.geojson')
    with open(geo_path, 'r') as gf:
        chi_wards = json.load(gf)
    tree = RTree()
    for i, a in enumerate(chi_wards['features']):
        shp = shape(a['geometry'])
        tree.insert({
            'idx': i,
            'shape': shp,
            'ward': a['properties']['ward']
        }, Rect(*shp.bounds))
    return chi_wards, tree


def load_rtree(geog):
    geog_tree = f'{geog}_tree'
    geog_func = zip_rtree if geog == 'zips' else ward_rtree
    if geog_tree not in g:
        setattr(g, geog_tree, geog_func())
    return getattr(g, geog_tree)


def handle_dates(start_date, end_date):
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start_date = date.today() - timedelta(days=365)
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end_date = date.today()

    return start_date, end_date


def call_issue_geog_query(cls, start_date, end_date, categories, zip_codes):
    filter_list = [cls.created_at >= start_date, cls.created_at <= end_date]
    if categories:
        filter_list.append(Categories.name.in_(categories.split(',')))
    if zip_codes:
        filter_list.append(Addresses.zip.in_(zip_codes.split(',')))

    return session.query(
        array_agg(Categories.name).label('categories'),
        cls.id.label('id'),
        cls.created_at.label('created_at'),
        Addresses.lat.label('lat'),
        Addresses.lon.label('lon'),
    ).outerjoin(
        cls.categories,
        Addresses,
    ).filter(*filter_list).order_by(cls.created_at.desc()).group_by(
        cls.id,
        cls.created_at,
        Addresses,
    ).distinct(cls.id, cls.created_at)


def handle_geog_filter(request, start_date, end_date):
    categories = request.args.get('categories')
    zip_codes = request.args.get('zip_codes')
    geog = request.args.get('geog', 'wards')

    combined_query = union_all(
        call_issue_geog_query(
            Calls, start_date, end_date, categories, zip_codes
        ),
        call_issue_geog_query(
            Issues, start_date, end_date, categories, zip_codes
        )
    ).alias('call_issues')

    chi_areas, tree = load_rtree(geog)

    for p in session.query(combined_query):
        if p.lon is None or p.lat is None:
            continue
        for r in tree.query_point((p.lon, p.lat)):
            if not r.leaf_obj():
                continue
            shp = r.leaf_obj()
            pt = Point(p.lon, p.lat)
            if pt.within(shp['shape']):
                props = chi_areas['features'][shp['idx']]['properties']
                if 'ci_count' not in props:
                    chi_areas[
                        'features'][shp['idx']]['properties']['ci_count'] = 0
                chi_areas['features'][shp['idx']]['properties']['ci_count'] += 1

    return chi_areas


@views.route('/filter-geo')
@login_required
def filter_geo():
    start_date, end_date = handle_dates(
        request.args.get('start_date'), request.args.get('end_date')
    )
    return jsonify(handle_geog_filter(request, start_date, end_date))


@views.route('/filter-csv')
@login_required
def filter_csv():
    start_date, end_date = handle_dates(
        request.args.get('start_date'), request.args.get('end_date')
    )
    chi_areas = handle_geog_filter(request, start_date, end_date)

    geog = request.args.get('geog', 'wards')
    categories = request.args.get('categories')

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    filename = 'sa_export_{}_{}_{}.csv'.format(
        start_date_str, end_date_str, geog
    )

    geog_name = geog[:-1]
    proxy = StringIO()
    writer = csv.writer(proxy)
    writer.writerow([start_date_str, end_date_str, categories, geog])
    writer.writerow([geog_name, 'ci_count'])

    for i in chi_areas['features']:
        writer.writerow([
            i['properties'][geog_name], i['properties']['ci_count']
        ])

    mem = BytesIO()
    mem.write(proxy.getvalue().encode('utf-8'))
    mem.seek(0)
    proxy.close()

    return send_file(
        mem,
        mimetype='text/csv',
        as_attachment=True,
        attachment_filename=filename
    )


@views.route('/detail-csv')
@login_required
def detail_csv():
    categories = request.args.get('categories')
    zip_codes = request.args.get('zip_codes')
    start_date, end_date = handle_dates(
        request.args.get('start_date'), request.args.get('end_date')
    )

    filter_list = []
    if categories:
        filter_list.append(Categories.name.in_(categories.split(',')))
    if zip_codes:
        filter_list.append(Addresses.zip.in_(zip_codes.split(',')))

    call_query = session.query(Calls).options(
        joinedload(Calls.address),
        joinedload(Calls.tenant),
        joinedload(Calls.landlord),
        joinedload(Calls.rep),
        subqueryload(Calls.categories),
    ).filter(
        Calls.created_at >= start_date,
        Calls.created_at <= end_date,
        *filter_list,
    ).order_by(Calls.created_at.asc())

    issue_query = session.query(Issues).options(
        joinedload(Issues.address),
        joinedload(Issues.tenant),
        joinedload(Issues.landlord),
        subqueryload(Issues.categories),
    ).filter(
        Issues.created_at >= start_date,
        Issues.created_at <= end_date,
        *filter_list,
    ).order_by(Issues.created_at.asc())

    calls = [RecordRow(c) for c in call_query]
    issues = [RecordRow(i) for i in issue_query]
    calls_issues = calls + issues

    chi_wards, tree = load_rtree('wards')

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
            if pt.within(shp['shape']):
                record.ward = shp['ward']

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    filename = 'sa_export_detail_{}_{}.csv'.format(start_date_str, end_date_str)

    proxy = StringIO()
    writer = csv.writer(proxy)
    writer.writerow(CSV_COLS)

    for record in calls_issues:
        writer.writerow(record.as_list())
    mem = BytesIO()
    mem.write(proxy.getvalue().encode('utf-8'))
    mem.seek(0)
    proxy.close()

    return send_file(
        mem,
        mimetype='text/csv',
        as_attachment=True,
        attachment_filename=filename
    )


@views.route('/')
@login_required
def index():
    return render_template('index.html')


@views.route('/breakdown')
@login_required
def breakdown():
    return render_template('breakdown.html')


@views.route('/print')
@login_required
def print_view():
    start_date, end_date = handle_dates(
        request.args.get('start_date'), request.args.get('end_date')
    )
    chi_areas = handle_geog_filter(request, start_date, end_date)

    # Handle report titles based on year and month
    if start_date.year == end_date.year:
        # If basic annual report, just return year
        if start_date.month == 1 and end_date.month == 12:
            report_time = start_date.year
        # If in same year, return Mon-Mon YYYY
        else:
            report_time = '{}-{} {}'.format(
                start_date.strftime('%b'), end_date.strftime('%b'),
                start_date.year
            )
    # If not same year, return Mon YYYY-Mon YYYY
    else:
        report_time = '{} {}-{} {}'.format(
            start_date.strftime('%b'), start_date.year, end_date.strftime('%b'),
            end_date.year
        )
    if request.args.get('report_title'):
        report_title = request.args.get('report_title')
    else:
        report_title = 'Calls and Issues: {}'.format(report_time)

    return render_template(
        'print.html',
        geo_dump=chi_areas,
        report_title=report_title,
        colors=request.args.get('color_choice', 'YlOrBr'),
        today=date.today()
    )

from __future__ import absolute_import, print_function, unicode_literals

from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, \
    stream_with_context, Response
from flask_login import login_required
import sqlalchemy
from sqlalchemy import select, union_all
from sqlalchemy.orm import joinedload, aliased
from sqlalchemy.dialects.postgresql import array_agg
from .database import db_session as session
from .models import User, Issues, Calls, Addresses, Categories
from .utils import point_in_poly
import StringIO
import json
import csv
import os

from shapely.geometry import shape, Point
from .pyrtree import Rect, RTree
import pickle
import time

views = Blueprint('views', __name__)

DETAIL_CSV_COLS = [
    'id',
    'call_issue',
    'created_at',
    'updated_at',
    'tenant_first_name',
    'tenant_last_name',
    'tenant_phone_number',
    'tenant_email',
    'street',
    'unit_number',
    'city',
    'state',
    'zip',
    'lat',
    'lon',
    'ward',
    'landlord_first_name',
    'landlord_last_name',
    'landlord_management_company',
    'landlord_email',
    'rep_first_name',
    'rep_last_name',
    'has_lease',
    'received_lead_notice',
    'number_of_children_under_six',
    'number_of_units_in_building',
    'is_owner_occupied',
    'is_subsidized',
    'subsidy_type',
    'is_rlto',
    'is_referred_by_info',
    'is_counseled_in_spanish',
    'referred_to_building_organizer',
    'categories',
    'title',
    'closed',
    'resolved',
    'area_of_residence',
    'efforts_to_fix',
    'message',
    'urgency',
    'entry_availability'
]


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
    filter_list = [
        cls.created_at >= start_date,
        cls.created_at <= end_date
    ]
    if categories:
        filter_list.append(
            Categories.name.in_(categories.split(','))
        )
    if zip_codes:
        filter_list.append(
            Addresses.zip.in_(zip_codes.split(','))
        )

    return session.query(
        Categories.name.label('category'),
        cls.id.label('id'),
        cls.created_at.label('created_at'),
        Addresses.lat.label('lat'),
        Addresses.lon.label('lon')
    ).outerjoin(cls.categories, Addresses
    ).filter(*filter_list
    ).order_by(cls.created_at.desc()
    ).distinct(cls.id, cls.created_at)


def handle_geog_filter(request, start_date, end_date):
    categories = request.args.get('categories')
    zip_codes = request.args.get('zip_codes')
    geog = request.args.get('geog', 'wards')

    combined_query = union_all(
        call_issue_geog_query(Calls, start_date, end_date, categories, zip_codes),
        call_issue_geog_query(Issues, start_date, end_date, categories, zip_codes)
    ).alias('call_issues')

    current_dir = os.path.dirname(__file__)
    geoj_path = os.path.join(
        current_dir, 'static', 'js', 'chi_{}.geojson'.format(geog)
    )
    with open(geoj_path, 'r') as gf:
        chi_areas = json.load(gf)

    [a['properties'].update({'ci_count': 0}) for a in chi_areas['features']]

    tree = RTree()
    # RTree indices are different than feature list, saving in obj
    for i, a in enumerate(chi_areas['features']):
        shp = shape(a['geometry'])
        tree.insert({'idx': i, 'shape': shp}, Rect(*shp.bounds))

    for p in session.query(combined_query):
        for r in tree.query_point((p.lon, p.lat)):
            if not r.leaf_obj():
                continue
            shp = r.leaf_obj()
            pt = Point(p.lon, p.lat)
            if pt.within(shp['shape']):
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

    filename = 'sa_export_{}_{}_{}.csv'.format(start_date_str, end_date_str, geog)

    def gen_csv_export():
        # Yield parameters and then column headers
        geog_name = geog[:-1]

        line = StringIO.StringIO()
        writer = csv.writer(line)

        writer.writerow([start_date_str, end_date_str, categories, geog])
        line.seek(0)
        yield line.read()
        line.truncate(0)

        writer.writerow([geog_name, 'ci_count'])
        line.seek(0)
        yield line.read()
        line.truncate(0)

        for i in chi_areas['features']:
            writer.writerow([i['properties'][geog_name], i['properties']['ci_count']])
            line.seek(0)
            yield line.read()
            line.truncate(0)

    return Response(
        stream_with_context(gen_csv_export()),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename={}'.format(filename)}
    )


@views.route('/detail-csv')
@login_required
def detail_csv():
    categories = request.args.get('categories')
    zip_codes = request.args.get('zip_codes')
    # geog = request.args.get('geog', 'wards')
    start_date, end_date = handle_dates(
        request.args.get('start_date'), request.args.get('end_date')
    )

    filter_list = []
    if categories:
        filter_list.append(
            Categories.name.in_(categories.split(','))
        )
    if zip_codes:
        filter_list.append(
            Addresses.zip.in_(zip_codes.split(','))
        )

    tenant = aliased(User)
    landlord = aliased(User)
    rep = aliased(User)

    call_query = session.query(
        Calls.id.label('id'),
        Calls.created_at.label('created_at'),
        Calls.updated_at.label('updated_at'),
        tenant.first_name.label('tenant_first_name'),
        tenant.last_name.label('tenant_last_name'),
        tenant.phone_number.label('tenant_phone_number'),
        tenant.email.label('tenant_email'),
        Addresses.street.label('street'),
        Addresses.unit_number.label('unit_number'),
        Addresses.city.label('city'),
        Addresses.state.label('state'),
        Addresses.zip.label('zip'),
        Addresses.lat.label('lat'),
        Addresses.lon.label('lon'),
        landlord.first_name.label('landlord_first_name'),
        landlord.last_name.label('landlord_last_name'),
        landlord.management_company.label('landlord_management_company'),
        landlord.email.label('landlord_email'),
        rep.first_name.label('rep_first_name'),
        rep.first_name.label('rep_first_name'),
        Calls.has_lease.label('has_lease'),
        Calls.received_lead_notice.label('received_lead_notice'),
        Calls.number_of_children_under_six.label('number_of_children_under_six'),
        Calls.number_of_units_in_building.label('number_of_units_in_building'),
        Calls.is_owner_occupied.label('is_owner_occupied'),
        Calls.is_subsidized.label('is_subsidized'),
        Calls.subsidy_type.label('subsidy_type'),
        Calls.is_rlto.label('is_rlto'),
        Calls.is_referred_by_info.label('is_referred_by_info'),
        Calls.is_counseled_in_spanish.label('is_counseled_in_spanish'),
        Calls.is_referred_to_building_organizer.label('referred_to_building_organizer'),
        sqlalchemy.func.array_to_string(
            array_agg(Categories.name), ',').label('categories')
    ).outerjoin(Calls.categories, Addresses
    ).outerjoin(tenant, Calls.tenant
    ).outerjoin(landlord, Calls.landlord
    ).outerjoin(rep, Calls.rep
    ).filter(*([Calls.created_at >= start_date, Calls.created_at <= end_date] + filter_list)
    ).order_by(Calls.created_at.asc()
    ).group_by(Calls, tenant, Addresses, landlord, rep)

    issue_query = session.query(
        Issues.id.label('id'),
        Issues.created_at.label('created_at'),
        Issues.updated_at.label('updated_at'),
        tenant.first_name.label('tenant_first_name'),
        tenant.last_name.label('tenant_last_name'),
        tenant.phone_number.label('tenant_phone_number'),
        tenant.email.label('tenant_email'),
        Addresses.street.label('street'),
        Addresses.unit_number.label('unit_number'),
        Addresses.city.label('city'),
        Addresses.state.label('state'),
        Addresses.zip.label('zip'),
        Addresses.lat.label('lat'),
        Addresses.lon.label('lon'),
        landlord.first_name.label('landlord_first_name'),
        landlord.last_name.label('landlord_last_name'),
        landlord.management_company.label('landlord_management_company'),
        landlord.email.label('landlord_email'),
        Issues.closed.label('closed'),
        Issues.resolved.label('resolved'),
        Issues.title.label('title'),
        Issues.message.label('message'),
        Issues.area_of_residence.label('area_of_residence'),
        Issues.efforts_to_fix.label('efforts_to_fix'),
        Issues.urgency.label('urgency'),
        Issues.entry_availability.label('entry_availability'),
        sqlalchemy.func.array_to_string(
            array_agg(Categories.name), ',').label('categories')
    ).outerjoin(Issues.categories, Addresses
    ).outerjoin(tenant, Issues.tenant
    ).outerjoin(landlord, Issues.landlord
    ).filter(*([Issues.created_at >= start_date, Issues.created_at <= end_date] + filter_list)
    ).order_by(Issues.created_at.asc()
    ).group_by(Issues, tenant, Addresses, landlord)

    calls = [dict(zip(c.keys(), c)) for c in call_query]
    issues = [dict(zip(i.keys(), i)) for i in issue_query]
    calls_issues = calls + issues

    current_dir = os.path.dirname(__file__)
    geoj_path = os.path.join(current_dir, 'static', 'js', 'chi_wards.geojson')
    with open(geoj_path, 'r') as gf:
        chi_areas = json.load(gf)

    [a['properties'].update({'ci_count': 0}) for a in chi_areas['features']]

    tree = RTree()
    for a in chi_areas['features']:
        shp = shape(a['geometry'])
        ward = a['properties']['ward']
        tree.insert({'ward': ward, 'shape': shp}, Rect(*shp.bounds))

    for ci in calls_issues:
        ci['call_issue'] = 'issue' if ci.get('title') else 'call'
        for r in tree.query_point((ci['lon'], ci['lat'])):
            if not r.leaf_obj:
                continue
            shp = r.leaf_obj()
            if shp is None:
                continue
            pt = Point(ci['lon'], ci['lat'])
            if pt.within(shp['shape']):
                ci['ward'] = shp['ward']

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    filename = 'sa_export_detail_{}_{}.csv'.format(start_date_str, end_date_str)

    def gen_csv_export():
        line = StringIO.StringIO()
        writer = csv.writer(line)

        writer.writerow(DETAIL_CSV_COLS)
        line.seek(0)
        yield line.read()
        line.truncate(0)

        for ci in calls_issues:
            writer.writerow(
                [unicode(ci.get(col, '')).encode('ascii', errors='ignore') for col in DETAIL_CSV_COLS]
            )
            line.seek(0)
            yield line.read()
            line.truncate(0)

    return Response(
        stream_with_context(gen_csv_export()),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename={}'.format(filename)}
    )


@views.route('/')
@login_required
def index():
    return render_template('index.html')


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
                start_date.strftime('%b'),
                end_date.strftime('%b'),
                start_date.year
            )
    # If not same year, return Mon YYYY-Mon YYYY
    else:
        report_time = '{} {}-{} {}'.format(
            start_date.strftime('%b'), start_date.year,
            end_date.strftime('%b'), end_date.year
        )

    return render_template('print.html',
                           geo_dump=chi_areas,
                           report_time=report_time,
                           colors=request.args.get('color_choice', 'YlOrBr'),
                           today=date.today())

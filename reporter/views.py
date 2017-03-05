from __future__ import absolute_import, print_function, unicode_literals

from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, \
    stream_with_context, Response
from flask_login import login_required
from sqlalchemy import select, union_all
from sqlalchemy.orm import joinedload
from .database import db_session as session
from .models import Issues, Calls, Addresses, Categories
from .utils import point_in_poly
import StringIO
import json
import csv
import os

views = Blueprint('views', __name__)


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


def call_issue_query(cls, start_date, end_date, categories, zip_codes):
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
    ).join(cls.categories, Addresses
    ).filter(*filter_list
    ).order_by(cls.created_at.desc()
    ).distinct(cls.id, cls.created_at)


def handle_filter(request, start_date, end_date):
    categories = request.args.get('categories')
    zip_codes = request.args.get('zip_codes')
    geog = request.args.get('geog', 'wards')

    combined_query = union_all(
        call_issue_query(Calls, start_date, end_date, categories, zip_codes),
        call_issue_query(Issues, start_date, end_date, categories, zip_codes)
    ).alias('call_issues')

    current_dir = os.path.dirname(__file__)
    geoj_path = os.path.join(
        current_dir, 'static', 'js', 'chi_{}.geojson'.format(geog)
    )
    with open(geoj_path, 'r') as gf:
        chi_areas = json.load(gf)

    [a['properties'].update({'call_issue_count': 0}) for a in chi_areas['features']]

    query_list = list(session.query(combined_query))
    for a in chi_areas['features']:
        a['properties']['call_issue_count'] = len(
            filter(lambda i: point_in_poly(
                i.lon, i.lat, a['geometry']['coordinates'][0]
                ), query_list)
        )
    return chi_areas


@views.route('/filter-geo')
@login_required
def filter_geo():
    start_date, end_date = handle_dates(
        request.args.get('start_date'), request.args.get('end_date')
    )
    return jsonify(handle_filter(request, start_date, end_date))


@views.route('/filter-csv')
@login_required
def filter_csv():
    start_date, end_date = handle_dates(
        request.args.get('start_date'), request.args.get('end_date')
    )
    chi_areas = handle_filter(request, start_date, end_date)

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

        writer.writerow([geog_name, 'call_issue_count'])
        line.seek(0)
        yield line.read()
        line.truncate(0)

        for i in chi_areas['features']:
            writer.writerow([i['properties'][geog_name], i['properties']['call_issue_count']])
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
    chi_areas = handle_filter(request, start_date, end_date)

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
                           today=date.today())

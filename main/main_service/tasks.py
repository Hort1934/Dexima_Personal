import datetime
import psycopg2
from psycopg2 import sql

from celery import shared_task
from dexima_ats_web_service.celery import app

from django.core.mail import send_mail
from django.core.cache import cache

from main_service.models import CustomUser, UserStatus
from dexima_ats_web_service.settings import EMAIL_HOST_USER

from config import ASSETS_POSTGRES_HOST, ASSETS_POSTGRES_DB, ASSETS_POSTGRES_USER, ASSETS_POSTGRES_PASSWORD, \
    ASSETS_POSTGRES_PORT


# 314-DB2Range
@app.task
def assets_range_calculator():
    all_asset_ranges = {}
    instrument = 'futures'  # spot
    timeframes = ['1s', '1m', '1h']  # '1d'
    connection = ''
    for timeframe in timeframes:
        try:
            # Connect to PostgreSQL database
            connection = psycopg2.connect(
                host=ASSETS_POSTGRES_HOST,
                database=ASSETS_POSTGRES_DB,
                user=ASSETS_POSTGRES_USER,
                password=ASSETS_POSTGRES_PASSWORD,
                port=ASSETS_POSTGRES_PORT
            )
            cursor = connection.cursor()

            # table_name = f"{exchange}_{instrument}_data_{timeframe}"
            table_name = f"dexima_{instrument}_data_{timeframe}"
            table_name_assets = "assets"

            # Retrieve unique asset_ids and their names
            unique_assets_query = sql.SQL(
                "SELECT DISTINCT d.asset_id, a.asset "
                "FROM {tablename} d "
                "JOIN {table_name_assets} a ON d.asset_id = a.id"
            ).format(
                tablename=sql.Identifier(table_name),
                table_name_assets=sql.Identifier(table_name_assets)
            )
            cursor.execute(unique_assets_query)
            unique_assets = cursor.fetchall()
            print(f'{len(unique_assets)} assets in {table_name}')

            asset_ranges = {}

            for asset_id, asset_name in unique_assets:
                # Retrieve the first and last timestamp for each asset
                date_range_query = sql.SQL(
                    "SELECT MIN(d.timestamp) as start_date, MAX(d.timestamp) as end_date "
                    "FROM {tablename} d "
                    "WHERE d.asset_id = %s"
                ).format(
                    tablename=sql.Identifier(table_name)
                )
                cursor.execute(date_range_query, (asset_id,))
                date_range = cursor.fetchone()
                start_date, end_date = date_range

                asset_ranges[f'dexima_{asset_name}_{instrument}_{timeframe}'] = {
                    "start_date": start_date.strftime('%Y-%m-%d %H:%M:%S'),
                    "end_date": end_date.strftime('%Y-%m-%d %H:%M:%S')
                }
            # Update the main dictionary with the results of this iteration
            all_asset_ranges.update(asset_ranges)

        except Exception as ex:
            print(ex)
            return 'assets_range_calculator work failed'
        finally:
            if connection:
                cursor.close()
                connection.close()

    cache.set('assets_range', all_asset_ranges, timeout=None)
    return f'assets_range_calculator work completed, {len(all_asset_ranges)}'


@app.task
def subscription_updater():
    sign = '\n\nWith best regards,\nats.trading team'
    try:
        for user in CustomUser.objects.filter(is_active=True):
            user_stats = UserStatus.objects.get(user_id=user.id)
            user_expired_date = user_stats.expiration_date
            time_left = (
                    user_expired_date - datetime.datetime.now(datetime.timezone.utc)
            ).days

            if time_left < 0:
                user.num_of_backtesting = 0
                user.num_of_optimization = 0
                user.num_of_ats = 0
                user.save()

                message = f'Dear {user.username}, the validity period of your account on ats.trading has expired.'

                get_time_left = cache.get(user.username)

                if not get_time_left:
                    send_email.delay(
                        'Expiration alert',
                        message + sign,
                        user.email)
                cache.set(user.username, message, timeout=None)
            elif 8 > time_left >= 0:
                future_date_str = user_expired_date.strftime('%Y-%m-%d')

                message = (f'Dear {user.username}, the term of validity of your account on ats.trading will expire in '
                           f'{time_left} days, on {future_date_str}. This will stop all services.')

                get_time_left = cache.get(user.username)

                if not get_time_left:
                    send_email.delay(
                        'Expiration alert',
                        message + sign,
                        user.email)
                cache.set(user.username, message, timeout=None)
            else:
                cache.delete(user.username)

        return 'completed'
    except Exception as e:
        print(e)
        return 'failed'


@shared_task
def send_email(subject, message, email):
    send_mail(subject, message, EMAIL_HOST_USER, [email])


@shared_task
def send_html_email(subject, message, email):
    send_mail(
        subject,
        '',
        EMAIL_HOST_USER,
        [email],
        html_message=message
    )


@shared_task
def send_confirmation_email(email, confirmation_link):
    sign = '<br><br>With best regards,<br>ats.trading team'
    subject = 'ats.trading email confirmation'

    html_message = f"""
    <html>
    <body>
        <p>Welcome!</p>
        <p>Please confirm your email address using the following link:</p>
        <p><a href="{confirmation_link}">Confirm Email</a></p>
        <p>{sign}</p>
    </body>
    </html>
    """

    send_mail(
        subject,
        '',
        EMAIL_HOST_USER,
        [email],
        html_message=html_message
    )


@shared_task
def send_alert_email(email, username, services_left, activity):
    if activity == 'backtest':
        activity = 'backtest/s'
    elif activity == 'optimize':
        activity = 'optimization/s'

    sign = '\n\nWith best regards,\nats.trading team'
    subject = 'Services balance notification'
    message = (f'Dear {username}, the balance of services on your account ats.trading is running out. '
               f'{services_left} {activity} left.')
    message = message + sign
    send_mail(subject, message, EMAIL_HOST_USER, [email])

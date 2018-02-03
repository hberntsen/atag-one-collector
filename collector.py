from urllib import request, parse
import json
from datetime import timedelta, datetime
import time
import pytz
from influxdb import InfluxDBClient

ATAG_ONE_IP = "192.168.46.10"
#from https://github.com/kozmoz/atag-one-api/blob/6f76619814f971ae4fc61eb69889caea8b5a363e/src/main/java/org/juurlink/atagone/AtagOneLocalConnector.java#L51
MESSAGE_INFO_CONTROL = 1
MESSAGE_INFO_SCHEDULES = 2
MESSAGE_INFO_CONFIGURATION = 4
MESSAGE_INFO_REPORT = 8
MESSAGE_INFO_STATUS = 16
MESSAGE_INFO_WIFISCAN = 32
MESSAGE_INFO_EXTRA = 64

def atag_time_to_datetime(atag_time):
    base = datetime(2000, 1, 1, 0, 0, 0, tzinfo=pytz.utc)
    return base + timedelta(seconds=atag_time)

def atag_request_data():
    data = json.dumps({
        'retrieve_message': {
            'seqnr': 0,
            'account_auth': {
                'user_account': "",
                'mac_address': "01:23:45:67:89:01"
                },
            'info': MESSAGE_INFO_CONTROL + MESSAGE_INFO_REPORT + MESSAGE_INFO_EXTRA
            }
        })

    #post request
    req = request.Request("http://" + ATAG_ONE_IP + ":10000/retrieve", data=str.encode(data))
    resp_raw = request.urlopen(req, timeout=10).read()
    resp = json.loads(resp_raw)['retrieve_reply']

    assert resp['acc_status'] == 2
    return resp

def create_influxdb_point(atag_resp):
    r = atag_resp['report']
    c = atag_resp['control']
    d = atag_resp['report']['details']

    # some fields are disabled because they did not provide any useful
    # information for me
    point = {
        'measurement': 'atag_one',
        'time': int(int(atag_time_to_datetime(r['report_time']).strftime('%s')) * 1e9),
        'fields': {
            'burning_hours': r['burning_hours'],
            'room_temp': r['room_temp'],
            'outside_temp': r['outside_temp'],
            #'pcb_temp': r['pcb_temp'],
            'ch_setpoint': r['ch_setpoint'],
            'dhw_water_temp': r['dhw_water_temp'],
            'ch_water_temp': r['ch_water_temp'],
            #'dhw_water_pres': r['dhw_water_pres'],
            'ch_water_pres': r['ch_water_pres'],
            'ch_return_temp': r['ch_return_temp'],
            'boiler_heating': r['boiler_status'] & 8 == 8,
            'ch_heating': r['boiler_status'] & 2 == 2,
            'dhw_heating': r['boiler_status'] & 4 == 4,
            #'ch_time_to_temp': r['ch_time_to_temp'],
            'power_cons': r['power_cons'],
            'current': r['current'],
            'boiler_temp': d['boiler_temp'],
            'boiler_return_temp': d['boiler_return_temp'],
            #'dhw_flow_rate': d['dhw_flow_rate'],
            #'min_mod_level': d['min_mod_level'],
            'rel_mod_level': d['rel_mod_level'],
            #'boiler_capacity': d['boiler_capacity'],
            'overshoot': d['overshoot'],
            'max_boiler_temp': d['max_boiler_temp'],
            'ch_status': c['ch_status'],
            'ch_mode_temp': c['ch_mode_temp'],
            'dhw_temp_setp': c['dhw_temp_setp'],
            'dhw_status': c['dhw_status'],
            #'dhw_mode': c['dhw_mode'],
            #'dhw_mode_temp': c['dhw_mode_temp']
        }
    }

    if r['outside_temp'] <= -100:
        del point['outside_temp']
    return point

time.sleep(10)
client = InfluxDBClient('influxdb', database='atagone')

while True:
    client.write_points([create_influxdb_point(atag_request_data())])
    time.sleep(10)

import requests


gps_msg = {
    'averageCog': 41,
    'iridium_latitude': 37.8192,
    'device_type': 'LEOPARD3',
    'lon': -122.27662,
    'sog': 0.1,
    'source': 'GPS',
    'battery': 88,
    'cep': 2,
    'momsn': 33,
    'id': 'zagvADYwKoPeWQxyJPeznlMrXJpVORdj',
    'power': False,
    'transmit_time': '2020-09-03T20:16:13Z',
    'lat': 37.82519,
    'txAt': '2020-09-03T20:16:13Z',
    'pdop': 3.0,
    'temp': 25.0,
    'JWT': 'eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJSb2NrIDciLCJpYXQiOjE1OTkxNjQxNzgsImFsdCI6IjUiLCJhdCI6IjIwMjAtMDktMDNUMjA6MDA6MDBaIiwiYXZlcmFnZUNvZyI6IjQxIiwiYXZlcmFnZVNvZyI6IjAuMCIsImJhdHRlcnkiOiI4OCIsImNlcCI6IjIiLCJjb2ciOiIwIiwiZGV2aWNlX3R5cGUiOiJMRU9QQVJEMyIsImlkIjoiemFndkFEWXdLb1BlV1F4eUpQZXpubE1yWEpwVk9SZGoiLCJpbWVpIjoiMzAwNTM0MDYwMjU3NDUwIiwiaXJpZGl1bV9sYXRpdHVkZSI6IjM3LjgxOTIiLCJpcmlkaXVtX2xvbmdpdHVkZSI6Ii0xMjIuMjY1NSIsImxhdCI6IjM3LjgyNTE5IiwibG9uIjoiLTEyMi4yNzY2MiIsIm1vbXNuIjoiMzMiLCJwZG9wIjoiMy4wMCIsInBvd2VyIjoiZmFsc2UiLCJzZXJpYWwiOiIyNTIzOCIsInNvZyI6IjAuMSIsInNvdXJjZSI6IkdQUyIsInRlbXAiOiIyNS4wIiwidHJhbnNtaXRfdGltZSI6IjIwMjAtMDktMDNUMjA6MTY6MTNaIiwidHJhbnNwb3J0IjoiSVJJRElVTSIsInRyaWdnZXIiOiJST1VUSU5FIiwidHhBdCI6IjIwMjAtMDktMDNUMjA6MTY6MTNaIn0.e-2apPXv_R9TJPXwQHhSAQAkuZHLFXh6X3kA_1W2BVJzWhU6Ap9tfws8_fDPOUKrQyXEg_VJicpJ0eDVa4SKxfzYjEBAlqnshPJvzv4I18cE5EWo_jtWNFyXUvQWePD6dGD4DCBNB4Q_A0w3dp60YtT9zNUXYSKnAkOOP_tS2cm3d01lCUXSy4dLZK4tfMvuqbvBo3C1A2YjT_Rvm0lxRWuyz-dD_zG-cOM5-TKlbxf04MfgGeJmSHDjBG9Igjl6hkuivW--p91oMiOqnSaDEyIyO1eisrwLWwm0d3Qy8DK-goKzb3PASI5lAa_fvXakmATVQjFGeQ2uiH8kBpGb5g',
    'alt': 5,
    'transport': 'IRIDIUM',
    'trigger': 'ROUTINE',
    'iridium_longitude': -122.2655,
    'averageSog': 0.0,
    'at': '2020-09-03T20:00:00Z',
    'serial': 25238,
    'imei': '300534060257450',
    'cog': 0}


ird_msg = {
    'txAt': '2020-09-03T20:16:13Z',
    'temp': 25.0,
    'iridium_latitude': 37.8192,
    'JWT': 'eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJSb2NrIDciLCJpYXQiOjE1OTkxNjQxNzksImF0IjoiMjAyMC0wOS0wM1QyMDoxNjoxNVoiLCJiYXR0ZXJ5IjoiODgiLCJjZXAiOiIyIiwiZGV2aWNlX3R5cGUiOiJMRU9QQVJEMyIsImlkIjoiYWJnckdYenBtTHFQRXl4ZGthS01XT3lvS0pka2VWTnYiLCJpbWVpIjoiMzAwNTM0MDYwMjU3NDUwIiwiaXJpZGl1bV9sYXRpdHVkZSI6IjM3LjgxOTIiLCJpcmlkaXVtX2xvbmdpdHVkZSI6Ii0xMjIuMjY1NSIsIm1vbXNuIjoiMzMiLCJwb3dlciI6ImZhbHNlIiwic2VyaWFsIjoiMjUyMzgiLCJzb3VyY2UiOiJJUklESVVNIiwidGVtcCI6IjI1LjAiLCJ0cmFuc21pdF90aW1lIjoiMjAyMC0wOS0wM1QyMDoxNjoxM1oiLCJ0cmFuc3BvcnQiOiJJUklESVVNIiwidHJpZ2dlciI6IlJPVVRJTkUiLCJ0eEF0IjoiMjAyMC0wOS0wM1QyMDoxNjoxM1oifQ.FAaFHJeoQDQ9DPcfVm-uzZgFBKZu5fhOh8m4qVdvT88Nc4MQIghz71SwDDjYZGpBJ4qPGdG_FS5_ivh-ZipEsu6buZcDayVtcHF_LYwopD8AecAY-W1D9WlMWaQpFa1FLMI7T6sr0yQx-4H1OqTKfz9xPDs134XjdOBbLSkqsXlDyGwOggpd_4dGw6Gj2AAAxq-5w3cqpr1Uq0P1dLHHD3eGU0Jpij4QUS4XBwTg1oxVX_V6hUba1NUFYKzxZjHEIA6lasI_Hp4ylI9yAn7py5RnQCv6CJbBX2L7GTzymUMNX5QsEv-gyyZEueVXD2tmgDk3_wW8KG3EeKA-Jnauag',
    'device_type': 'LEOPARD3',
    'transport': 'IRIDIUM',
    'source': 'IRIDIUM',
    'trigger': 'ROUTINE',
    'iridium_longitude': -122.2655,
    'battery': 88,
    'cep': 2,
    'momsn': 33,
    'at': '2020-09-03T20:16:15Z',
    'serial': 25238,
    'imei': '300534060257450',
    'id': 'abgrGXzpmLqPEyxdkaKMWOyoKJdkeVNv',
    'power': False,
    'transmit_time': '2020-09-03T20:16:13Z'}

ack_msg = {
    'txAt': '2020-09-03T21:10:45Z',
    'temp': 0.0,
    'iridium_latitude': 37.8192,
    'JWT': 'eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJSb2NrIDciLCJpYXQiOjE1OTkxNjc0NTAsImF0IjoiMjAyMC0wOS0wM1QyMToxMDo0N1oiLCJiYXR0ZXJ5IjoiMCIsImNlcCI6IjMiLCJkZXZpY2VfdHlwZSI6IkxFT1BBUkQzIiwiaWQiOiJnd3lOUHBEbWViSkxCWG1OeWF3eG5vQVJxeE1kWk9WRyIsImltZWkiOiIzMDA1MzQwNjAyNTc0NTAiLCJpcmlkaXVtX2xhdGl0dWRlIjoiMzcuODE5MiIsImlyaWRpdW1fbG9uZ2l0dWRlIjoiLTEyMi4yNjU1IiwibWVzc2FnZV9hY2siOiIxMjQxOTYiLCJtb21zbiI6IjM2IiwicG93ZXIiOiJmYWxzZSIsInNlcmlhbCI6IjI1MjM4Iiwic291cmNlIjoiSVJJRElVTSIsInRlbXAiOiIwLjAiLCJ0cmFuc21pdF90aW1lIjoiMjAyMC0wOS0wM1QyMToxMDo0NVoiLCJ0cmFuc3BvcnQiOiJJUklESVVNIiwidHJpZ2dlciI6IkFDS05PV0xFREdFIiwidHhBdCI6IjIwMjAtMDktMDNUMjE6MTA6NDVaIn0.ee5YnRv0n0vmw0l2j2muBs7cRyah2JOa3eEAL9hmaJ8B1YSKqnMhFfQfYVaiSrfw4opH00MoUIrLOzXaxuZ4Hh4hJe5rqIeUuSaYTyzy4J2pANRRXz1xFHFQXLJGty9mZ992vu5doxlB8LDliiv4A_nmVU3A7FQdW1DX5XoJ0n5ESAx3P9KiftcBr6LbEYz_96M6r10oUwoKaZGeeOx2100R47XPjrmFF3AywKsickTZ3QKQX3JUrsAAuqzu2Pl6jGfbiFa6Wk2dTBiflA3AjTZhjdC6HSgK3T8iaZKEQuZ0uZZlTJkGwwyagwrF5gpN0za-aMDXgooTsT8QvTpIAg',
    'device_type': 'LEOPARD3',
    'transport': 'IRIDIUM',
    'source': 'IRIDIUM',
    'trigger': 'ACKNOWLEDGE',
    'message_ack': 124196,
    'iridium_longitude': -122.2655,
    'battery': 0,
    'cep': 3,
    'momsn': 36,
    'at': '2020-09-03T21:10:47Z',
    'serial': 25238,
    'imei': '300534060257450',
    'id': 'gwyNPpDmebJLBXmNyawxnoARqxMdZOVG',
    'power': False,
    'transmit_time': '2020-09-03T21:10:45Z'
}


def post_msg(msg):
    URL = "https://paikea.localhost:8888/rockstar/incoming"
    requests.post(URL, msg)

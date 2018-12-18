#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 22 08:56:33 2018

@author: skoebric
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import geocoder
import geopandas as gpd

Countiesshpfile = "/Users/skoebric/Dropbox/shp files/cb_2017_us_county_20m/cb_2017_us_county_20m.shp"
Countiesshp = gpd.read_file(Countiesshpfile)
#Countiesshp = Countiesshp.to_crs({'init': 'esri:102009'}) #conical

state_codes = {'53': 'WA', '10': 'DE', '11': 'DC', '55': 'WI','54': 'WV','15': 'HI','12': 'FL','56': 'WY','72': 'PR','34': 'NJ','35': 'NM',
               '48': 'TX','22': 'LA','37': 'NC','38': 'ND','31': 'NE','47': 'TN','36': 'NY','42': 'PA','02': 'AK','32': 'NV','33': 'NH',
               '51': 'VA','08': 'CO','06': 'CA','01': 'AL','05': 'AR','50': 'VT','17': 'IL','13': 'GA','18': 'IN','19': 'IA','25': 'MA',
               '04': 'AZ','16': 'ID','09': 'CT','23': 'ME','24': 'MD','40': 'OK','39': 'OH','49': 'UT','29': 'MO','27': 'MN','26': 'MI',
               '44': 'RI','20': 'KS','30': 'MT','28': 'MS','45': 'SC','21': 'KY','41': 'OR','46': 'SD'}
state_codes.pop("72") #remove Puerto Rico

Countiesshp = Countiesshp.loc[Countiesshp['STATEFP'].isin(list(state_codes.keys()))]

def stateusps(row):
    return state_codes[row['STATEFP']]

Countiesshp['STUSPS'] = Countiesshp.apply(stateusps, axis = 1)

def FIPcountystatestring(row):
    FIP = str(row['STATEFP']) + str(row['COUNTYFP'])
    return FIP

Countiesshp['fip'] = Countiesshp.apply(FIPcountystatestring, axis=1)

countydf = pd.read_excel('/Users/skoebric/Dropbox/Resilience/Resilience Heat Map 9-14-18.xlsx',
                         sheet_name = 'Updates 9-14-18')

def fipstringer(row):
    fip_in = str(row['fip']).split('.')[0]
    if len(fip_in) < 5:
        fip_in = '0' + fip_in
    return fip_in

countydf['fip'] = countydf.apply(fipstringer, axis = 1)

def countylookuper(row):
    fip_in = row['fip']
    matches = countydf.loc[countydf['fip'] == fip_in]
    if len(matches) > 1:
        print(fip_in, 'ERROR df is too long')
    elif len(matches) == 0:
        print(fip_in, 'ERROR df is empty, no FIP match')
    elif len(matches) == 1:
        return matches

def indlooker(row):
    matches = countylookuper(row)
    ResilInd = float(matches['res_ind'])
    LMIburd = float(matches['energy_burden_lmi'])
    AirSea = float(matches['air_sea'])
    RevCap = float(matches['rev'])
    FEMAspend = float(matches['total_FEMA_spend'])
    return ResilInd, LMIburd, AirSea, RevCap, FEMAspend

Countiesshp['tuples'] = Countiesshp.apply(indlooker, axis = 1)
Countiesshp['resil_ind'] = [i[0] for i in Countiesshp['tuples']]
Countiesshp['lmi_burd'] = [i[1] for i in Countiesshp['tuples']]
Countiesshp['air_sea'] = [i[2] for i in Countiesshp['tuples']]
Countiesshp['rev'] = [i[3] for i in Countiesshp['tuples']]
Countiesshp['total_FEMA_spend'] = [i[4] for i in Countiesshp['tuples']]

Countiesshp['air_sea'].fillna(0, inplace = True)
Countiesshp = Countiesshp.to_crs({'init': 'epsg:4326'})

xwdf = gpd.read_file('/Users/skoebric/Dropbox/Resilience/susceptibility_extreme_weather/susceptibility_extreme_weatherPolygon.shp')
xwdf = xwdf.fillna(0)
xwdf = xwdf.replace('None', 0)
xwdf = xwdf.replace('Low', 1)
xwdf = xwdf.replace('Moderate',2)
xwdf = xwdf.replace('Medium',3)
xwdf = xwdf.replace('High',4)
xwdf = xwdf.replace('Extreme',5)
xwdf['fip'] = [i[0:5] for i in xwdf['geoid']]

xwdf = xwdf[['geoid',
 'state_abbr',
 'county_nam',
 'flood_risk',
 'cyclone_ri',
 'drought_ri',
 'gid',
 'risk',
 'fip']]

floodlist = []
droughtlist = []
cyclonelist = []
risklist = []

for fip in Countiesshp.GEOID:
    df_ = xwdf.loc[xwdf['fip'] == fip]
    if len(df_) > 0:
        floodlist.append(round(df_['flood_risk'].mean()))
        droughtlist.append(round(df_['drought_ri'].mean()))
        cyclonelist.append(round(df_['cyclone_ri'].mean()))
        risklist.append(round(df_['risk'].mean()))
    elif len(df_) == 0:
        floodlist.append(0)
        droughtlist.append(0)
        cyclonelist.append(0)
        risklist.append(0)

Countiesshp['floodrisk'] = floodlist
Countiesshp['droughtrisk'] = droughtlist
Countiesshp['cyclonerisk'] = cyclonelist
Countiesshp['risk'] = risklist

Cshp = Countiesshp[['GEOID','geometry','resil_ind','lmi_burd','rev','total_FEMA_spend',
                    'floodrisk', 'droughtrisk', 'cyclonerisk', 'risk']]
#%%
import multiprocessing
import geocoder 
import pandas as pd
import time
import requests
from multiprocessing.dummy import Pool as ThreadPool 

participants = pd.read_excel('/Users/skoebric/Dropbox/GitHub/resilmap/Participant_List.xlsx')
participants = participants.drop_duplicates(subset = ['City','State'])
participants = participants[['City', 'State']]
participants = participants.dropna(how = 'any')
participants['geocoderstring'] = participants['City'] + ' ' + participants['State'] + ' USA'

def geocode_worker(inputrow):
    try:
        r = geocoder.mapquest(inputrow, key = 'rszS6XG8TKX2oHEIiJexOAHiMwdYYxCS')
        lat = r.lat
        lng = r.lng
        print(r)
    except Exception:
        lat = None
        lng = None
        print('fail')
    return lat, lng

def multithreadgeocoder(inputlist):
    start = time.time()
    pool = ThreadPool(20)
    outputtuples = pool.map(geocode_worker, inputlist)
    outputlist = []
    for t in outputtuples:
        try:
            outputlist.append([float(t[1]),float(t[0])])
        except TypeError:
            outputlist.append('fail')
    print(time.time() - start)
    return outputlist

participants['lat_lng'] = multithreadgeocoder(list(participants['geocoderstring']))

#%%
participants = participants.loc[participants['lat_lng'] != 'fail']
from shapely.geometry import Point
import geopandas as gpd

participants['geometry'] = participants['lat_lng'].apply(Point)
participants = gpd.GeoDataFrame(participants, geometry = 'geometry')

def point_in_polygon_worker(inputgeometry):
    def pointpasser(row):
        return inputgeometry.contains(row.geometry)
    allcities = participants.apply(pointpasser, axis = 1)
    if allcities.sum() == 0:
        print(False)
        return False
    else:
        print(True)
        return True
    
def cityincountychecker(inputlist):
    start = time.time()
    pool = ThreadPool(40)
    outputlist = pool.map(point_in_polygon_worker, inputlist)
    print(time.time() - start)
    return outputlist

Cshp['contains_participant'] = cityincountychecker(list(Cshp['geometry']))

#%%
plt.cla()
import seaborn as sns
#Cshp = Cshp.loc[Cshp['rev'] < Cshp['rev'].quantile(.95)]
#Cshp = Cshp.loc[Cshp['total_FEMA_spend'] < Cshp['total_FEMA_spend'].quantile(.95)]
#Cshp = Cshp.loc[Cshp['rev'] > Cshp['rev'].quantile(.05)]
#Cshp = Cshp.loc[Cshp['total_FEMA_spend'] > Cshp['total_FEMA_spend'].quantile(.05)]
resilquantile = []
for r in Cshp['resil_ind']:
    if r < 0.25:
        resilquantile.append('1')
    elif r < 1:
        resilquantile.append('2')
    elif r < 1.5:
        resilquantile.append('3')
    elif r < 2:
        resilquantile.append('4')
    else:
        resilquantile.append('5')

Cshp['resquant'] = resilquantile
sns.lmplot(x = 'risk', y = 'total_FEMA_spend', hue = 'resquant', data = Cshp)

    
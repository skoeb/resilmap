#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 17 15:34:48 2018

@author: skoebric
"""

import geopandas as gpd
import pandas as pd
pd.options.mode.chained_assignment = None
from shapely.geometry import Point
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import folium
from folium import FeatureGroup

class PandasAssembler(object):
    def __init__(self):
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
            RevCap = float(matches['rev_per_cap'])
            FEMAspend = float(matches['FEMA_spend'])
            return ResilInd, LMIburd, AirSea, RevCap, FEMAspend
        
        Countiesshp['tuples'] = Countiesshp.apply(indlooker, axis = 1)
        Countiesshp['resil_ind'] = [i[0] for i in Countiesshp['tuples']]
        Countiesshp['lmi_burd'] = [i[1] for i in Countiesshp['tuples']]
        Countiesshp['air_sea'] = [i[2] for i in Countiesshp['tuples']]
        Countiesshp['rev_per_cap'] = [i[3] for i in Countiesshp['tuples']]
        Countiesshp['FEMA_spend'] = [i[4] for i in Countiesshp['tuples']]
        
        Countiesshp['air_sea'].fillna(0, inplace = True)
        Countiesshp = Countiesshp.to_crs({'init': 'epsg:4326'})
        Cshp = Countiesshp[['GEOID','geometry','resil_ind','lmi_burd','rev_per_cap','FEMA_spend']]
        
        
        def hexcolormapper(df, column, colorscale, quantile = 0.95, clip = False):
            norm = matplotlib.colors.Normalize(vmin=min(df[column]), vmax=df[column].quantile(quantile), clip=False)
            mapper = plt.cm.ScalarMappable(norm=norm, cmap=colorscale)
            df[f'{column}_color'] = df[column].apply(lambda x: mcolors.to_hex(mapper.to_rgba(x)))
            return df
        
        Cshp = hexcolormapper(Cshp, 'resil_ind', plt.cm.Greens, quantile = 0.975)
        Cshp = hexcolormapper(Cshp, 'lmi_burd', plt.cm.Reds, quantile = 0.975)
        Cshp = hexcolormapper(Cshp, 'rev_per_cap', plt.cm.Blues, quantile = 0.975)
        Cshp = hexcolormapper(Cshp, 'FEMA_spend', plt.cm.Oranges, quantile = 0.975)
        
        Cshp['resil_ind'] = round(Cshp['resil_ind'],2)
        Cshp['lmi_burd'] = round(Cshp['lmi_burd'],1)
        Cshp['rev_per_cap'] = round(Cshp['rev_per_cap'])
        Cshp['FEMA_spend'] = round(Cshp['FEMA_spend'])
        
        self.Cshp = Cshp
        
        citiesdf = pd.read_csv('/Users/skoebric/Dropbox/Resilience/energy_cohort.csv')
        
        def latlonglister(row):
            lat = row['lat']
            long = row['long']
            return [lat, long]
        
        def styler(row):
            pop = row['pop_class_desc']
            climate = row['ashrae_climate_zone_desc']
            cl = ['#4169e1','#5079e6','#5d8aea','#908dd1','#d37480','#f6532e','#f63b1a','#e92a2d','#dc143c']
            if climate == 'Subarctic':
                color = cl[0]
            elif climate == 'Very Cold':
                color = cl[1]
            elif climate == 'Cold':
                color = cl[2]
            elif climate == 'Cool':
                color = cl[3]
            elif climate == 'Mixed':
                color = cl[4]
            elif climate == 'Warm':
                color = cl[5]
            elif climate == 'Hot':
                color = cl[6]
            elif climate == 'Very Hot':
                color = cl[7]
            if pop == '0 to 2,500':
                size = 1
            elif pop == '2,500+ to 10,000':
                size = 1
            elif pop == '10,000+ to 50,000':
                size = 1
            elif pop == '50,000+ to 175,000':
                size = 1000
            elif pop == '175,000+ to 500,000':
                size = 10000
            elif pop == '500,000+':
                size = 15000
            return color, size
        
        citiesdf['tuples'] = citiesdf.apply(styler, axis = 1)
        citiesdf['color'] = [i[0] for i in citiesdf['tuples']]
        citiesdf['size'] = [i[1] for i in citiesdf['tuples']]
        
        citiesdf['lat_long'] = citiesdf.apply(latlonglister, axis = 1)
        Citiesshp = citiesdf.copy()
        
        self.sm_Citiesshp = Citiesshp.loc[Citiesshp['pop_class_desc'] == '50,000+ to 175,000']
        self.md_Citiesshp = Citiesshp.loc[Citiesshp['pop_class_desc'] == '175,000+ to 500,000']
        self.lg_Citiesshp = Citiesshp.loc[Citiesshp['pop_class_desc'] == '500,000+']   
        
        world = gpd.read_file('/Users/skoebric/Dropbox/GitHub/resilmap/geometry/world.geojson')
        self.usa = world.loc[world['ADM0_A3'] == 'USA']
        
        def pointinpolygonchecker(row):
            geom = row['geometry']
            return self.usa.geometry.contains(geom)
        def latlonglister2(row):
            geom = str(row['geometry'])
            geom = geom.replace('POINT (','').replace(')','')
            geom = geom.split(' ')
            long = float(geom[0])
            lat = float(geom[1])
            return [lat, long]
        
        airports = gpd.read_file('geometry/ne_10m_airports/ne_10m_airports.shp')
        airports['inusa'] = airports.apply(pointinpolygonchecker, axis = 1)
        airports = airports.loc[airports['inusa'] == True]
        airports['lat_long'] = airports.apply(latlonglister2, axis = 1)
        self.airports = airports[['type','name','lat_long','iata_code']]
        seaports = gpd.read_file('geometry/ne_10m_ports/ne_10m_ports.shp')
        seaports['inusa'] = seaports.apply(pointinpolygonchecker, axis = 1)
        seaports = seaports.loc[seaports['inusa'] == True]
        seaports['lat_long'] = seaports.apply(latlonglister2, axis = 1)
        self.seaports = seaports[['name','lat_long']]
        
    
    def mapper(self):
        m = folium.Map(location=[39.5, -98.4], zoom_start=4, tiles = 'stamentoner', prefer_canvas = True, world_copy_jump=True, no_wrap=True)
        folium.TileLayer('openstreetmap').add_to(m)

        med_cities_fg = FeatureGroup(name='Cities Between 175,000 and 500,000', show = False)
        large_cities_fg = FeatureGroup(name='Cities Larger than 500,000', show = True)
        res_ind_fg = FeatureGroup(name='Resilience Indicator', show = True)
        lmi_burd_fg = FeatureGroup(name='LMI Energy Buden', show = False)
        rev_per_cap_fg = FeatureGroup(name = 'Revenue Per Capita', show = False)
        FEMA_spend_fg = FeatureGroup(name = 'FEMA Spending Per Capita', show = False)
        ports_fg = FeatureGroup(name = 'Air/Sea Ports', show = False)
        
        
        
        for index, row in self.airports.iterrows():
            airporticon = folium.features.CustomIcon('https://image.flaticon.com/icons/svg/579/579268.svg', icon_size = (20,20))
            ports_fg.add_child(folium.map.Marker(location = row['lat_long'], icon=airporticon,
                                                 popup = (
                                                         f"<b>Airport Code:</b> {row['iata_code']}<br>"
                                                         f"<b>Type:</b> {row['type']}")))
        for index, row in self.seaports.iterrows():
            seaporticon = folium.features.CustomIcon('https://image.flaticon.com/icons/svg/1198/1198475.svg', icon_size = (20,20))
            ports_fg.add_child(folium.map.Marker(location = row['lat_long'], icon=seaporticon,
                                                 popup = (
                                                         f"<b>Port</b><br>"
                                                         f"<b>Name:</b> {row['name']}"))) 

        
        
        for index, row in self.md_Citiesshp.iterrows():
            med_cities_fg.add_child(folium.Circle(location=row['lat_long'],
                                                 radius = (row['size'] + row['pop']/200),color=row['color'],
                                                 fill_color = row['color'],fill = True, fill_opacity = 0.7,
                                                 popup = (
                                                    f"<b><i>{row['name']}, {row['state_abbr']}</b></i><br>"
                                                    f"<b>Population:</b> {row['pop_class_desc']}<br>"
                                                    f"<b>Climate Zone:</b> {row['ashrae_climate_zone_desc']}<br>"
                                                    f"<b>Residential Consumption:</b> {row['res_elec_mwh']} MWh<br>"
                                                    f"<b>Commercial Consumption:</b> {row['comm_elec_mwh']} MWh<br>"
                                                    f"<b>Industrial Consumption:</b> {row['ind_elec_mwh']} MWh<br>"
                                                 )))
            
        for index, row in self.lg_Citiesshp.iterrows():
            large_cities_fg.add_child(folium.Circle(location=row['lat_long'],
                                                 radius = (row['size'] + row['pop']/200),color=row['color'],
                                                 fill_color = row['color'],fill = True, fill_opacity = 0.7,
                                                 popup = (
                                                    f"<b><i>{row['name']}, {row['state_abbr']}</b></i><br>"
                                                    f"<b>Population:</b> {row['pop_class_desc']}<br>"
                                                    f"<b>Climate Zone:</b> {row['ashrae_climate_zone_desc']}<br>"
                                                    f"<b>Residential Consumption:</b> {row['res_elec_mwh']} MWh<br>"
                                                    f"<b>Commercial Consumption:</b> {row['comm_elec_mwh']} MWh<br>"
                                                    f"<b>Industrial Consumption:</b> {row['ind_elec_mwh']} MWh<br>"
                                                 )))
                    
        for index, row in self.Cshp.loc[self.Cshp['resil_ind'] > 0].iterrows():
            geojson_ = folium.GeoJson(self.Cshp.loc[index:index+1],
                              style_function = lambda feature: {
                                  'fillColor': feature['properties']['resil_ind_color'],
                                  'fillOpacity':0.5,
                                  'color': feature['properties']['resil_ind_color'],
                                  'opacity': 0.6,
                                  'weight':0.5}) 
                                            
            popup_ = folium.Popup(
                      f"<b>County FIP:</b> {row['GEOID']}<br>"
                      f"<b>Resilience Indicator:</b> {row['resil_ind']}<br>"
                      f"<b>LMI Burden:</b> {row['lmi_burd']*100}%<br>"
                      f"<b>Rev Per Cap:</b> ${row['rev_per_cap']}<br>"
                      f"<b>FEMA Spending:</b> ${row['FEMA_spend']}<br>"
                      )
            popup_.add_to(geojson_)
            geojson_.add_to(res_ind_fg)
            
        for index, row in self.Cshp.loc[self.Cshp['lmi_burd'] > 0].iterrows():
            geojson_ = folium.GeoJson(self.Cshp.loc[index:index+1],
                              style_function = lambda feature: {
                                  'fillColor': feature['properties']['lmi_burd_color'],
                                  'fillOpacity':0.5,
                                  'color': feature['properties']['lmi_burd_color'],
                                  'opacity': 0.6,
                                  'weight':0.5}) 
                                            
            popup_ = folium.Popup(
                      f"<b>County FIP:</b> {row['GEOID']}<br>"
                      f"<b>Resilience Indicator:</b> {row['resil_ind']}<br>"
                      f"<b>LMI Burden:</b> {row['lmi_burd']*100}%<br>"
                      f"<b>Rev Per Cap:</b> ${row['rev_per_cap']}<br>"
                      f"<b>FEMA Spending:</b> ${row['FEMA_spend']}<br>"
                      )
            popup_.add_to(geojson_)
            geojson_.add_to(lmi_burd_fg)
            
        for index, row in self.Cshp.loc[self.Cshp['rev_per_cap'] > 0].iterrows():
            geojson_ = folium.GeoJson(self.Cshp.loc[index:index+1],
                              style_function = lambda feature: {
                                  'fillColor': feature['properties']['rev_per_cap_color'],
                                  'fillOpacity':0.5,
                                  'color': feature['properties']['rev_per_cap_color'],
                                  'opacity': 0.6,
                                  'weight':0.5}) 
                                            
            popup_ = folium.Popup(
                      f"<b>County FIP:</b> {row['GEOID']}<br>"
                      f"<b>Resilience Indicator:</b> {row['resil_ind']}<br>"
                      f"<b>LMI Burden:</b> {row['lmi_burd']*100}%<br>"
                      f"<b>Rev Per Cap:</b> ${row['rev_per_cap']}<br>"
                      f"<b>FEMA Spending:</b> ${row['FEMA_spend']}<br>"
                      )
            popup_.add_to(geojson_)
            geojson_.add_to(rev_per_cap_fg)
            
        for index, row in self.Cshp.loc[self.Cshp['FEMA_spend'] > 0].iterrows():
            geojson_ = folium.GeoJson(self.Cshp.loc[index:index+1],
                              style_function = lambda feature: {
                                  'fillColor': feature['properties']['FEMA_spend_color'],
                                  'fillOpacity':0.5,
                                  'color': feature['properties']['FEMA_spend_color'],
                                  'opacity': 0.6,
                                  'weight':0.5}) 
                                            
            popup_ = folium.Popup(
                      f"<b>County FIP:</b> {row['GEOID']}<br>"
                      f"<b>Resilience Indicator:</b> {row['resil_ind']}<br>"
                      f"<b>LMI Burden:</b> {row['lmi_burd']*100}%<br>"
                      f"<b>Rev Per Cap:</b> ${row['rev_per_cap']}<br>"
                      f"<b>FEMA Spending:</b> ${row['FEMA_spend']}<br>"
                      )
            popup_.add_to(geojson_)
            geojson_.add_to(FEMA_spend_fg)
        

        m.add_child(res_ind_fg)
        m.add_child(lmi_burd_fg)
        m.add_child(rev_per_cap_fg)
        m.add_child(FEMA_spend_fg)
        m.add_child(ports_fg)
        m.add_child(med_cities_fg)
        m.add_child(large_cities_fg)
        
        m.keep_in_front(med_cities_fg, large_cities_fg, ports_fg)
        m.add_child(folium.map.LayerControl(collapsed = False, autoZIndex = True))
    
        self.html = m
        return self

    def saver(self):
        self.html.save('/Users/skoebric/Dropbox/GitHub/resilmap/index.html')
#%%
        
#xwdf = gpd.read_file('/Users/skoebric/Dropbox/Resilience/susceptibility_extreme_weather/susceptibility_extreme_weatherPolygon.shp')
#for county in set(self.Cshp['GEOID'])
#xwdf = xwdf.fillna(0)
#xwdf = xwdf.replace('None', 0)
#xwdf = xwdf.replace('Low', 1)
#xwdf = xwdf.replace('Moderate',2)
#xwdf = xwdf.replace('Medium',3)
#xwdf = xwdf.replace('High',4)
#xwdf = xwdf.replace('Extreme',5)
#
#xwdf = xwdf[['geoid','flood_risk','cyclone_ri','drought_ri','geometry']]
#
#import folium
#m = folium.Map(location=[48, -102], zoom_start=3, prefer_canvas= True)
#m.choropleth(geo_data = xwdf, data = xwdf, key_on = 'feature.properties.geoid',
#            columns = ['geoid','flood_risk'], fill_color='BuGn', line_weight = 0.2, line_opacity = 0.5,
#            fill_opacity = 0.4, legend_name = 'Flood Risk',
#            threshold_scale = [0,1,2,3,4,5],
#            smooth_factor = 100)
#m.save('/Users/skoebric/Desktop/test.html')
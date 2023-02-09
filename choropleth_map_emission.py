import pandas as pd
import h3
import json
from geojson.feature import *
import plotly.graph_objs as go
import geopandas as gpd
from shapely import wkt
import numpy as np

def list_of_valid_hex(gdf,reso):
    
    exp=[]
    for polygon in gdf.geometry:
        # Convert Polygon to GeoJSON dictionary
        poly_geojson = gpd.GeoSeries([polygon]).__geo_interface__
        # Parse out geometry key from GeoJSON dictionary
        poly_geojson = poly_geojson['features'][0]['geometry'] 
        # Fill the dictionary with Resolution 10 H3 Hexagons

        h3_hexes = h3.polyfill_geojson(poly_geojson, reso)
        exp.append(h3_hexes)
    exp=list(set().union(*exp))
    
    return exp

def sum_by_hexagon(df,resolution,pol,fr,to,pc_res_8=[],pc_res_5=[],vessel_type=[]):
    """
    Use h3.geo_to_h3 to index each data point into the spatial index of the specified resolution.
    Use h3.h3_to_geo_boundary to obtain the geometries of these hexagons
    
    Ex counts_by_hexagon(data, 8)
    """
    
    if vessel_type:
        df_aggreg=df[((df.date_time.between(fr,to))&(df.StandardVesselType.isin(vessel_type)))]
    else:
        df_aggreg=df[df.date_time.between(fr,to)]
    if df_aggreg.shape[0]>0: 
        df_aggreg=df_aggreg.assign(res_5=df_aggreg.res_8.apply(lambda x: h3.h3_to_parent(x,5)))

        df_aggreg=df_aggreg.assign(res_mixed=np.where(((df_aggreg.res_8.isin(pc_res_8))|(df_aggreg.res_5.isin(pc_res_5))),df_aggreg.res_8,
                                                  df_aggreg.res_5))
                                                  
               
        df_aggreg=df_aggreg[~df_aggreg.res_mixed.isin(pc_res_5)]

        if resolution==8:
            df_aggreg = df_aggreg.groupby(by = "res_mixed").agg({"co2_t":sum,"ch4_t":sum,"n2o_t":sum}).reset_index()
            df_aggreg.rename(columns={"res_mixed":"hex_id"},inplace=True)
        elif resolution<=5:
            df_aggreg = df_aggreg.assign(new_res= df_aggreg.res_8.apply(lambda x: h3.h3_to_parent(x,resolution)))

            df_aggreg = df_aggreg.groupby(by = "new_res").agg({"co2_t":sum,"ch4_t":sum,"n2o_t":sum}).reset_index()
            df_aggreg.rename(columns={"new_res":"hex_id"},inplace=True)
            
        else:
            df_aggreg = df_aggreg.assign(new_res=np.where(df_aggreg.res_8.isin(pc_res_8),
                                            df_aggreg.res_8.apply(lambda x: h3.h3_to_parent(x,resolution)),
                                            df_aggreg.res_mixed))

            df_aggreg = df_aggreg.groupby(by = "new_res").agg({"co2_t":sum,"ch4_t":sum,"n2o_t":sum}).reset_index()
            df_aggreg.rename(columns={"new_res":"hex_id"},inplace=True)
 
        df_aggreg=df_aggreg[["hex_id", "co2_t","ch4_t","n2o_t"]]
  
        df_aggreg["geometry"] =  df_aggreg.hex_id.apply(lambda x: 
                                                                {    "type" : "Polygon",
                                                                      "coordinates": 
                                                                    [h3.h3_to_geo_boundary(x,geo_json=True)]
                                                                }
                                                            )
        
        return df_aggreg
    else:
        return df_aggreg

def hexagons_dataframe_to_geojson(df_hex, file_output = None):
    """
    Produce the GeoJSON for a dataframe that has a geometry column in geojson 
    format already, along with the columns hex_id and value
    
    Ex counts_by_hexagon(data)
    """    
   
    list_features = []
    
    for i,row in df_hex.iterrows():
        feature = Feature(geometry = row["geometry"] , id=row["hex_id"], properties = {"value" : row["value"]})
        list_features.append(feature)
        
    feat_collection = FeatureCollection(list_features)
    
    geojson_result = json.dumps(feat_collection)
    
    #optionally write to file
    if file_output is not None:
        with open(file_output,"w") as f:
            json.dump(feat_collection,f)
    
    return geojson_result 


def choropleth_map(ghg, df_aggreg,layout_in,fill_opacity = 0.8):
    
    """
    Creates choropleth maps given the aggregated data.
    """    

    df_aggreg.rename(columns={ghg:"value"},inplace=True)  
    #colormap
    min_value = df_aggreg["value"].min()
    max_value = df_aggreg["value"].max()
    m = round ((min_value + max_value ) / 2 , 0)
    
    #take resolution from the first row
    res = h3.h3_get_resolution(df_aggreg.loc[0,'hex_id'])
    
    #create geojson data from dataframe
    geojson_data = json.loads(hexagons_dataframe_to_geojson(df_hex = df_aggreg))
    
    ##plot on map
    initial_map=go.Choroplethmapbox(geojson=geojson_data,
                                    locations=df_aggreg.hex_id.tolist(),
                                    z=df_aggreg["value"].round(2).tolist(),
                                    colorscale="Reds",
                                    marker_opacity=fill_opacity,
                                    marker_line_width=1,
                                    colorbar = dict(thickness=20, ticklen=3,title="tonnes"),
                                    hovertemplate = '%{z:,.2f}<extra></extra>')
    
    initial_map=go.Figure(data=initial_map,layout=layout_in)
    
    return initial_map
    

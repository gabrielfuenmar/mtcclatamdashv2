
'''
Author:Gabriel Fuentes
gabriel.fuentes@snf.no'''

# Import required libraries
import pathlib
import dash
import numpy as np
from dash.dependencies import Input, Output, State, ClientsideFunction
from dash import dcc
from dash import html
import plotly.figure_factory as ff
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from dateutil.relativedelta import *
from datetime import datetime
import calendar

from controls import TYPE_COLORS,PORTS_COLORS,FLEET,pc_res_8, pc_res_5
from choropleth_map_emission import choropleth_map, sum_by_hexagon

##DataFrames
from data_filtering import processed_data
import pandas as pd
import geopandas as gpd
import os
import requests
import boto3
import h3
from collections import defaultdict

AWS_KEY=os.environ.get('AWS_KEY', None)
AWS_SECRET=os.environ.get('AWS_SECRET', None)

session = boto3.Session( aws_access_key_id=AWS_KEY,
                         aws_secret_access_key=AWS_SECRET)

s3 = session.resource('s3')

bucket_list=[]
for file in  s3.Bucket("mtcclatam").objects.filter(Prefix='dash/'):
    file_name=file.key
    if "_all" not in file_name.split("/")[-1].split("&")[-1].split(".")[0]:
      bucket_list.append(file.key)
    
for file in bucket_list:
    if "emissions" in file.split("/")[1]:
        em=pd.read_csv(s3.Object("mtcclatam", file).get()['Body'])
        em=em.assign(year_month=em.year_month.apply(str))
        
        last_update=datetime.fromisoformat(file.split("/")[-1].split("&")[-1].split(".")[0]).strftime("%d %b %Y")
        
        ###months before or first position
        fr_update=(datetime.fromisoformat(file.split("/")[-1].split("&")[-1].split(".")[0])-relativedelta(months=1)).replace(day=1)

        if fr_update<datetime.fromisoformat("2024-01-01"):
            fr_update=datetime.fromisoformat("2024-01-01")
                  
        to_update=datetime.fromisoformat(file.split("/")[-1].split("&")[-1].split(".")[0])
        
        em['year_month_str'] = em['year_month'].astype(str)
        
        # Adjust the lambda to handle YYYYM format correctly by appending a '0' prefix to months if necessary
        em = em.assign(
            date_time=em['year_month_str'].apply(lambda x: datetime.strptime(x[0:4] + "-" + x[4:].rjust(2, '0') + "-" + str(calendar.monthrange(int(x[:4]), int(x[4:].rjust(2, '0')))[1]), "%Y-%m-%d")),
            month=em.year_month_str.apply(lambda x: int(x[4:].rjust(2, '0'))),
            year=em.year_month_str.apply(lambda x: int(x[:4]))
        )
        
        # Using np.where to conditionally update date_time
        em = em.assign(
            date_time=np.where(
                (em["month"] == to_update.month) & (em["year"] == to_update.year),
                datetime.fromisoformat("{}-{}-{}".format(to_update.year, str(to_update.month).zfill(2), str(to_update.day).zfill(2))),
                em.date_time
            )
        )
        em["date_time"]=pd.to_datetime(em.date_time)
        ###Slders info
        fr_slider=fr_update.strftime("%d %b %Y")
        to_slider=to_update.strftime("%d %b %Y")
        
        range_months=pd.period_range(fr_update,to_update,freq="M").strftime("%b %Y").tolist()
        
        
        slider_dic={}
        if len(range_months)<5:
            for x in range(0,len(range_months),1):
                if x <=len(range_months):
                    slider_dic[x]=range_months[x]
            slider_dic[list(slider_dic.keys())[-1]+1]=""
            steps=1
        else:
            for x in range(0,len(range_months),5):
                if x <=len(range_months):
                    slider_dic[x]=range_months[x]
            slider_dic[list(slider_dic.keys())[-1]+1]=""
            steps=5
        
        ### Emissions this month all co2e
        this_month="{}{}".format(datetime.today().year,datetime.today().month)
        em=em.assign(ch4_t=em.ch4_t*27,
                     n2o_t=em.n2o_t*273)
        
        co2e=int(em[em.year_month==this_month][["co2_t","ch4_t","n2o_t"]].sum().sum())
        
    elif "stops_all" in file.split("/")[1]:
        ports=pd.read_csv(s3.Object("mtcclatam", file).get()['Body'])
    elif "transits" in file.split("/")[1]:
        canal=pd.read_csv(s3.Object("mtcclatam", file).get()['Body'])
    
ports,canal=processed_data(FLEET,ports,canal)

canal=canal.assign(port_name=np.where(canal.direction=="South","Panama Canal South","Panama Canal North"))
       
gatun=pd.read_csv("https://evtms-rpts.pancanal.com/eng/h2o/Download_Gatun_Lake_Water_Level_History.csv")
gatun.rename(columns={"DATE_LOG":"date","GATUN_LAKE_LEVEL(FEET)":"level_meters"},inplace=True)
    
gatun=gatun.assign(level_meters=gatun.level_meters*0.3048,
                          date=pd.to_datetime(gatun["date"]))


##Databases
panama_ports=gpd.read_file("data/Panama_ports.geojson")


pol=gpd.read_file("data/Panama_Canal.geojson")[["Name","geometry"]]
pol=pol[pol.geometry.apply(lambda x: x.geom_type=="Polygon")]

##Transform to datetime. Preferred to read csv method which is less flexible.
canal["lock_in"]=pd.to_datetime(canal["lock_in"])
ports["stop_time_in"]=pd.to_datetime(ports["stop_time_in"])

##Ports color
panama_ports=panama_ports.assign(color="#F9A054")

# get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("data").resolve()

app = dash.Dash(
    __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}]
)

app.title = 'Panama Maritime Statistics'

server = app.server

# Create global chart template
MAPBOX_TOKEN = os.environ.get('MAPBOX_TOKEN', None)

layout_map = dict(
    autosize=True,
    paper_bgcolor='#175A7F',
    plot_bgcolor='#30333D',
    margin=dict(l=10, r=10, b=10, t=10),
    hovermode="closest",
    font=dict(family="HelveticaNeue",size=17,color="#F8F8F8"),
    legend=dict(font=dict(size=10), orientation="h"),
    mapbox=dict(
        accesstoken=MAPBOX_TOKEN,
        style='mapbox://styles/gabrielfuenmar/ckhs87tuj2rd41amvifhb26ad',
        center=dict(lon=-79.55, lat=8.93),
        zoom=9,
    ),
    showlegend=False,
)

layout= dict(
    legend=dict(bgcolor='rgba(0,0,0,0)',font=dict(size=14,family="HelveticaNeue")),
    font_family="HelveticaNeue",
    font_color="#707070",
    title_font_family="Neutraface-text",
    title_font_color="#707070",
    title_font_size=20,
    paper_bgcolor='#F8F8F8',
    plot_bgcolor='#F8F8F8',
    xaxis=dict(gridcolor="rgba(178, 178, 178, 0.4)",title_font_size=15,
                tickfont_size=14,title_font_family="HelveticaNeue",tickfont_family="HelveticaNeue"),
    yaxis=dict(gridcolor="rgba(178, 178, 178, 0.4)",title_font_size=15,tickfont_size=14,
                title_font_family="HelveticaNeue",tickfont_family="HelveticaNeue")
    )

##Modebar on graphs
config={"displaylogo":False, 'modeBarButtonsToRemove': ['autoScale2d']}


##Annotation on graphs
annotation_layout=dict(
    xref="paper",
    yref="paper",
    align='left',
    x=0.25,
    y=-0.35,
    borderwidth=0)

# Create app layout
app.layout = html.Div(
    [
        dcc.Store(id="aggregate_data"),
        # empty Div to trigger javascript file for graph resizing
        html.Div(id="output-clientside"),
        html.Div(
            [
                html.Div(
                    [
                        html.A(html.Img(
                            src=app.get_asset_url("mtcc_logo_v5.png"),
                            id="plotly-image",
                            style={
                                "height": "160px",
                                "width": "auto",
                                "margin-bottom": "0px",
                                "text-align": "center"
                            },
                        ),
                            href="https://mtcclatinamerica.com/")
                    ],
                    className="one-half column",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3(
                                    "Panama Maritime Statistics",
                                    style={"margin-bottom": "0px",
                                            "font-family":'"Neutraface-text",Helvetica,Arial,sans-serif'},
                                ),
                                html.H5(
                                    "Efficiency and Sustainability Indicators", style={"margin-top": "0px"}
                                ),
                            ]
                        )
                    ],
                    className="one-half column",
                    id="title",
                ),
                html.Div(
                    [
                        html.Button("Refresh", id="refresh-button"), 
                        html.A(
                            html.Button("Developer", id="home-button"),
                            href="https://logistikk.io",
                        )                  
                    ],
                    className="one-third column",
                    id="button",
                    style={
                        "text-align": "right"},
                ),
            ],
            id="header",
            className="row flex-display",
            style={"margin-bottom": "15px"},
        ),
        html.Div(
            [
                html.Div(
                    [
                      html.Div([  
                          html.P("Date Filter",
                                        className="control_label",
                                    ),
                                    html.Div([html.P(id="date_from"),
                                    html.P(id="date_to")],className="datecontainer")
                                ,
                            dcc.RangeSlider(
                                id="year_slider",
                                min=0,
                                max=list(slider_dic.keys())[-1],
                                step=steps,
                                value=[0, list(slider_dic.keys())[-1]],
                                marks=slider_dic,
                                allowCross=False,
                                className="dcc_control",
                            ),
                            html.P("Vessel Type", className="control_label"),
                            dcc.Dropdown(
                                id='types-dropdown',
                                options=[{'label': row,'value': row} \
                                          for row in sorted(FLEET)],
                                        placeholder="All",multi=True,
                                        style={"color": "#707070",},
                                        className="dcc_control"),
                            html.P("Port:", className="control_label"),
                            dcc.Dropdown(
                                id='ports-dropdown',
                                options=[{'label': row,'value': row} \
                                          for row in sorted(ports[~ports.port_name.isin(["Pacific - PATSA","Colon2000"])]\
                                                                  .dropna(subset=["port_name"]).port_name.unique())+["Panama Canal South", "Panama Canal North"]],
                                        placeholder="All",multi=True,
                                        style={"color": "#707070",},
                                        className="dcc_control"),
                            html.P(
                                "Vessel Size (GT)",
                                className="control_label",
                            ),
                            html.Div([html.P(id="size_from"),
                                    html.P(id="size_to")],className="datecontainer"),
                            
                            dcc.RangeSlider(
                                id="size_slider",
                                min=400,
                                max=170000,
                                value=[400, 170000],
                                step=8500,
                                marks={
                                    400:"400",
                                    35000:"35k",
                                    70000:"70k",
                                    105000:"105k",
                                    140000:"140k",
                                    170000:"170k"},
                                allowCross=False,
                                className="dcc_control",
                            ),
                        html.P(
                            "Emissions gas",
                            className="control_label",
                        ),
                        dcc.Dropdown(
                            id='selector',
                            options=[{'label': 'Carbon Dioxide', 'value': 'co2_t'},
                                      {'label': 'Methane', 'value': 'ch4_t'},
                                      {'label': 'Nitrous Oxide', 'value': 'n2o_t'}],
                                    placeholder="Carbon Dioxide",multi=False,
                                    value='co2_t',
                                    style={"color": "#707070",},
                                    className="dcc_control")],
                              className="pretty_container",
                              style={"padding":"none",
                                      "box-shadow":"none"},
                              id="cross-filter-options_top"
                              ),
                    html.Div([
                        
                        html.P(
                            "Latest update",
                            className="control_label",
                        ),
                        html.Div([
                                html.Div(html.P("{}".format(last_update),id="from_alg",
                                                style={"font-size":"1.6em"}),className="mini_container"),
                            ],
                            style={"display":"flex",
                                    "flex-direction":"row",
                                    "justify-content":"center"})],
                        className="pretty_container",
                        style={"padding":"none",
                                "box-shadow":"none"},
                        id="cross-filter-options_bot",
                        ),        
                    ],
                    className="pretty_container four columns",
                    style={"display":"flex",
                            "flex-direction":"column",
                            "justify-content":"space-between"},
                    id="cross-filter-options_all", 
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [html.H6(id="waitingText"), html.P("Waiting Average")],
                                    id="waiting",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="opsText"), html.P("Operations")],
                                    id="ops",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="serviceText"), html.P("Service Average")],
                                    id="service_m",
                                    className="mini_container",
                                ),
                                html.Div(#####Hardcoded for the time being. Build a scrapper.
                                    [dcc.Loading([html.H6(id="co2etext")],id="loading_co2e",type="circle"), 
                                                  dcc.Markdown(children="""$$CO_{2}e$$ (tonnes)""",mathjax=True)],
                                    id="co2etext_box",
                                    className="mini_container",
                                ),
                            ],
                            id="info-container",
                            className="row container-display",
                        ),
                        html.Div([
                            html.Div(
                                    [
                                        html.Div([html.H5("Emissions Review"),
                                                  html.H6(id="month_map",style={"color":"white"})],
                                                            style={"display": "flex", "flex-direction": "row","justify-content":"space-between"}),
                                        dcc.Loading([dcc.Graph(animate=False,config=config,id="map_in")],id="loading_icon_map",type="circle"),
                                              html.P(["Grid size"],id="grid_size",className="control_label"),
                                                          dcc.Slider(
                                                          id="zoom_slider",
                                                          min=4,
                                                          max=8,
                                                          value=8,
                                                          marks={4:{'label': '1'},5:{'label': '2'},6:{'label': '3'},
                                                            7:{'label': '4'},8:{'label': '5'}},
                                                          className="dcc_control",
                                                          included=False),
                                            ],
                                id="emissionsMapContainer",
                                className="pretty_container eight columns",
                                )
                            ],
                            className="row flex-display",
                            ),
                        ],
                    id="right-column",
                    className="eight columns",
                ),
            ],
            className="row flex-display",
        ),
        html.Div(
            [
                html.Div(
                    [dcc.Loading([dcc.Graph(id="service_graph",config=config)],id="loading_icon_ser",type="circle")],
                    className="pretty_container six columns",
                ),
                html.Div(
                    [dcc.Loading([dcc.Graph(id="op_phase_type",config=config)],id="loading_icon_rat",type="circle")],
                    className="pretty_container six columns",
                )
            ],
            className="row flex-display",
        ),
        html.Div(
            [
                html.Div(
                    [dcc.Loading([dcc.Graph(id="draught_graph",config=config)],id="loading_icon_dr",type="circle")],
                    className="pretty_container six columns",
                ),
                html.Div(
                    [dcc.Loading([dcc.Graph(id="waiting_graph",config=config)],id="loading_icon_wait",type="circle")],
                    className="pretty_container six columns",
                )
            ],
            className="row flex-display",
        ),
    ],
    id="mainContainer",
    style={"display": "flex", "flex-direction": "column"},
)

    
def upper_text_p1(fr=em.date_time.min(),to=em.date_time.max(),ports_sel=["All"],
                type_vessel=["All"],size=["All"],text_bar=True,*args):
    
    date_from=fr
    date_to=to
    
    em_in=em.copy()
    
    canal_in=canal[(canal.lock_in.between(date_from,date_to))&(canal.direct_transit==True)].\
        copy()
    ports_in=ports[ports.stop_time_in.between(date_from,date_to)].\
        copy()
    canal_in=canal_in.assign(day=canal_in.lock_in.dt.date)
    
    canal_in=canal_in[["day","waiting_time","service_time","port_name","StandardVesselType","GrossTonnage"]]
    canal_in["day"]=pd.to_datetime(canal_in.day)
    ports_in=ports_in.assign(day=ports_in.stop_time_in.dt.date)
    ports_in=ports_in[["day","waiting_time","service_time","port_name","StandardVesselType","GrossTonnage"]]
    ports_in["day"]=pd.to_datetime(ports_in.day)
    
    em_in=em_in[em_in.date_time.between(date_from,date_to)]
    df_in=pd.concat([ports_in,canal_in],axis=0)
    
    if "All" not in ports_sel:
        df_in=df_in[df_in.port_name.isin(ports_sel)]
    
    if "All" not in size:
        df_in=df_in[df_in.GrossTonnage.between(size[0],size[1])]
        
    if "All" not in type_vessel:
        df_in=df_in[df_in["StandardVesselType"].isin(type_vessel)]
        
    if text_bar is True: ##Row at top with summary values
        waiting_mean=df_in.waiting_time.mean()
        ops=df_in.shape[0]
        service_mean=df_in.service_time.mean()

        return waiting_mean,ops,service_mean
    
    else: ###Graphs on waiting, service time and draught ratio
        
        labels_w=[]
        remove_w=[]
        waiting=[]
        
        for name,row in df_in.groupby("port_name"):
            if len(row.waiting_time.dropna().tolist())>25:      
                labels_w.append(name)
                wa_li=row.waiting_time[(row.waiting_time>1)&(row.waiting_time<row.waiting_time.quantile(0.95))&\
                                        (row.waiting_time>row.waiting_time.quantile(0.05))]
                waiting.append(wa_li.dropna().tolist())
            else:
                remove_w.append(name)
                
        labels_s=[]
        remove_s=[]
        service=[]
    
        
        for name,row in df_in.groupby("port_name"):
            if len(row.service_time.dropna().tolist())>25:  
                labels_s.append(name)
                se_li=row.service_time[(row.service_time>0)&(row.service_time<row.service_time.quantile(0.95))&\
                        (row.service_time>row.service_time.quantile(0.05))]
                service.append(se_li.dropna().tolist())
            else:
                remove_s.append(name)
                
        #### Box plot on waiting times and lines on emissions      
        
        em_in=em_in[["StandardVesselType","co2_t","ch4_t","n2o_t"]].groupby("StandardVesselType").sum().sum(axis=1).reset_index()
        
        em_in.rename(columns={0:"co2e_t"},inplace=True)
        
        em_in=em_in[em_in.StandardVesselType.isin(ports.StandardVesselType.unique().tolist())]
        em_in=em_in.sort_values(by="StandardVesselType")
        
        
        box_info=defaultdict(list)
        
        ports_in=ports.copy()
        ports_in=ports_in.sort_values(by="StandardVesselType")
        for ind,row in ports_in.iterrows():
            if pd.isna(row.waiting_time) :
                continue
            else:
                box_info[row.StandardVesselType].append(row.waiting_time)
        
        fig_box=make_subplots(specs=[[{"secondary_y": True}]])   
        if bool(box_info):
            for s in box_info:
                fig_box.add_trace(go.Box(y=box_info[s], quartilemethod="inclusive", name=s,
                                         marker_color=TYPE_COLORS[s]),secondary_y=False )
            fig_box.add_trace(go.Scatter(x=em_in.StandardVesselType, y=em_in.co2e_t, mode='lines',
                                         line=dict(shape="linear", width=2,color="#808080",dash='dash')),
                              secondary_y=True)
                
            fig_box.update_layout(layout,yaxis=dict(zeroline=True,linecolor="rgba(178, 178, 178, 0.4)",title_text="Hours")
                                      ,title_text="<b>Waiting Time and Emissions per type</b>",
                                      showlegend=False,)
            fig_box.update_yaxes(title_text="CO2e tonnes", secondary_y=True)
        
             
        ##Figs of waiting and service time
        
        if len(labels_w)>0:
            fig_waiting = ff.create_distplot(waiting, labels_w,histnorm="probability density",
                                              colors=list(PORTS_COLORS.values()),show_rug=False,show_curve=False)
            
        else:
            fig_waiting=go.Figure()
        
        if len(labels_s)>0:
            fig_service = ff.create_distplot(service, labels_s,histnorm="probability density",
                                              colors=list(PORTS_COLORS.values()),show_rug=False,show_curve=False)
        else:
            fig_service=go.Figure()
        
        
        ###Service and Waiting Graphs Layout
        fig_waiting.update_layout(layout,yaxis=dict(zeroline=True,linecolor='#707070',title_text="Density"),
                                  xaxis=dict(title_text="Hours"),
                                  legend=dict(x=0.6),title_text="<b>Waiting Time</b>")
        fig_waiting.update_traces(marker_line_color='rgb(8,48,107)',
                                  marker_line_width=1.5, opacity=0.8)
        fig_service.update_layout(layout,yaxis=dict(zeroline=True,linecolor="#707070",title_text="Density"),
                                  xaxis=dict(title_text="Hours"),
                                  legend=dict(x=0.6),title_text="<b>Service Time</b>")
        fig_service.update_traces(marker_line_color='rgb(8,48,107)',
                                  marker_line_width=1.5, opacity=0.8)
        
        
        return fig_service,fig_waiting,fig_box
        
def lake_draught(fr="",to="",*args):
    gatun_in=gatun.copy()
    
    to=gatun_in["date"].max()
    fr=to-relativedelta(months=18)
    
    date_from=pd.to_datetime(fr)
    
    date_to=pd.to_datetime(to)
    
    gatun_in=gatun_in[gatun_in.date.between(date_from,date_to)]
    gatun_in=gatun_in.assign(day=gatun_in.date.dt.day.astype(str)+"/"+gatun_in.date.dt.month.astype(str)+"/"+gatun_in.date.dt.year.astype(str))
    lake_fig=make_subplots(specs=[[{"secondary_y": True}]])
    lake_fig.add_trace(go.Scatter(
                name="Gatun Lake Depth",
                mode="lines",
                x=gatun_in.day,y=gatun_in.level_meters,
                line=dict(shape="spline", width=4,color="#6671FD")))
    
    
    ##Layout update  
    lake_fig.update_layout(layout,title_text="<b>Gatun Lake level</b>",
                            xaxis=dict(title_text="Date",nticks=6),
                            legend=dict(x=0.6,y=1))
    
    # Set y-axes titles
    lake_fig.update_yaxes(title_text="Lake Depth (m)", gridcolor="rgba(178, 178, 178, 0.4)",
                          title_font_size=15,tickfont_size=14,
                          title_font_family="HelveticaNeue",tickfont_family="HelveticaNeue",
                          range=[gatun_in.level_meters.min()*0.99,gatun_in.level_meters.max()*1.05])
    lake_fig.add_annotation(annotation_layout,text="*Uncontrolled values sourced from the Panama Canal Authority")
    return lake_fig
    
def emissions_map(ghg,res,date_fr=em.date_time.min(),
                  date_to=em.date_time.max(),lat=None,lon=None,zoom=None,type_vessel=[]):
    
    emissions_in=em.copy()
    
    df_aggreg=sum_by_hexagon(emissions_in,res,pol,date_fr,
                              date_to,pc_res_8=pc_res_8,pc_res_5=pc_res_5,vessel_type=type_vessel)
    
    
    ##Update layout
    if lat is not None:
        layout_map["mapbox"]["center"]["lon"]=lon
        layout_map["mapbox"]["center"]["lat"]=lat
        layout_map["mapbox"]["zoom"]=zoom
        
    if df_aggreg.shape[0]>0:
        heatmap=choropleth_map(ghg,df_aggreg,layout_map)
    else:
        heatmap=go.Figure(data=go.Scattermapbox(lat=[0],lon=[0]),layout=layout_map)

    return heatmap

##Upper Row,
@app.callback(
    [
        Output("waitingText", "children"),
        Output("opsText", "children"),
        Output("serviceText", "children"),
        Output("date_from","children"),
        Output("date_to","children"),
        Output("size_from","children"),
        Output("size_to","children"),
    ],
    [Input("ports-dropdown", "value"),
      Input("types-dropdown","value"),
      Input('year_slider', 'value'),
      Input('size_slider', 'value'),
      ],
)
def update_row1(ports_val,types_val,date,size_val):
    if not ports_val:
        ports_val=["All"]
    if not types_val:
        types_val=["All"]
            
    date_fr=fr_update+relativedelta(months=+date[0])
 
    if date[1]==len(range_months):
        date_to=to_update
    else:
        date_to=fr_update+relativedelta(months=+date[1])
    
    if date[0]==0:
        date_fr=fr_update   
    
    waiting,ops,service=upper_text_p1(fr=date_fr,to=date_to,ports_sel=ports_val,type_vessel=types_val,size=size_val)
    
    date_fr=date_fr.strftime('%d-%m-%Y')
    date_to=date_to.strftime('%d-%m-%Y')
    
    return "{:.1f}".format(waiting)+ " hours", format(ops,","), "{:.1f}".format(service) + " hours",\
        date_fr, date_to ,format(size_val[0],","),format(size_val[1],",")
    

@app.callback(
    [  Output("service_graph", "figure"),
        Output("waiting_graph", "figure"),
        Output("op_phase_type", "figure")
    ],
    [Input("ports-dropdown", "value"),
      Input("types-dropdown","value"),
      Input('year_slider', 'value'),
      Input('size_slider', 'value'),
      ],
)


def update_graphs(ports_val,types_val,date,size_val):
    if not ports_val:
        ports_val=["All"]
    if not types_val:
        types_val=["All"]
  
    date_fr=fr_update+relativedelta(months=+date[0])
    
    if date[1]==len(range_months):
        date_to=to_update
    else:
        date_to=fr_update+relativedelta(months=+date[1])
    
    if date[0]==0:
        date_fr=fr_update
    
    service_g,waiting_g,box_graph=upper_text_p1(fr=date_fr,to=date_to,ports_sel=ports_val,
                                      type_vessel=types_val,size=size_val,text_bar=False)
    
    return service_g,waiting_g,box_graph

@app.callback(
    Output("draught_graph", "figure"),
    [ Input('year_slider', 'value'),
      ],
)

def update_gatun(date):

    date_fr=fr_update+relativedelta(months=+date[0])
 
    if date[1]==len(range_months):
        date_to=to_update
    else:
        date_to=fr_update+relativedelta(months=+date[1])
    
    if date[0]==0:
        date_fr=fr_update
        
    date_fr=date_fr.strftime('%d-%m-%Y')
    date_to=date_to.strftime('%d-%m-%Y')
        
    lake_g=lake_draught(fr=date_fr,to=date_to)
    
    return lake_g

@app.callback(
    Output("map_in", "figure"),
    [Input("selector","value"),
      Input("zoom_slider","value"),
      Input('year_slider', 'value'),
      Input("types-dropdown","value"),
      ],
    [State("map_in","relayoutData")]
)

def update_emissions_map(ghg_t,resol,date,types_val,relay):
    
    date_fr=fr_update+relativedelta(months=+date[0])
 
    if date[1]==len(range_months):
        date_to=to_update
    else:
        date_to=fr_update+relativedelta(months=+date[1])
    
    if date[0]==0:
        date_fr=fr_update
    
    if relay is not None:   
        if "mapbox.center" in relay.keys():
            lat=relay["mapbox.center"]["lat"]
            lon=relay["mapbox.center"]["lon"]
            zoom=relay["mapbox.zoom"]
        else:
            lat=8.93
            lon=-79.55
            zoom=9
    else:
        lat=8.93
        lon=-79.55
        zoom=9
    
    if "All" in types_val:
        types_val=[]
    
    if ghg_t is None:
        ghg_t="co2_t"
    ####Size deactived for the time being.
    emission_fig=emissions_map(ghg_t,resol,date_fr=date_fr,date_to=date_to,lat=lat,lon=lon,zoom=zoom,type_vessel=types_val)
        
    return emission_fig 

###Month and type update on map
@app.callback(
      Output("month_map", "children"),
    [ Input('year_slider', 'value'),
      ],
)

def month_map(date):
    date_fr=fr_update+relativedelta(months=+date[0])
 
    if date[1]==len(range_months):
        date_to=to_update
    else:
        date_to=fr_update+relativedelta(months=+date[1])
    
    if date[0]==0:
        date_fr=fr_update

    date_fr=date_fr.strftime("%d %b %Y")
    date_to=date_to.strftime("%d %b %Y")
    
    m_e="{} to {}".format(date_fr,date_to)
    
    return m_e


###Month and type update on map
@app.callback(
      Output("co2etext", "children"),
    [ Input("selector","value"),
      Input('year_slider', 'value'),
      Input("types-dropdown","value"),
      ],
)

def co2e_text(ghg_t,date,type_vessel):
    
    date_fr=fr_update+relativedelta(months=+date[0])
 
    if date[1]==len(range_months):
        date_to=to_update
    else:
        date_to=fr_update+relativedelta(months=+date[1])

    if date[0]==0:
        date_fr=fr_update
    
    em_in=em.copy()
    
    if ghg_t is None:
        ghg_t="co2_t"
        
    if not type_vessel or "All" in type_vessel:
        em_in=int(em_in[em_in.date_time.between(date_fr,date_to)][[ghg_t]].sum().sum())

    else:
        em_in=int(em_in[((em_in.date_time.between(date_fr,date_to))&\
                        (em_in.StandardVesselType.isin(type_vessel)))][[ghg_t]].sum().sum()) 
       
    result=f"{em_in:,}"
    return result

##Refresh button
@app.callback([Output("ports-dropdown", "value"),
                Output("types-dropdown","value"),
                Output('year_slider', 'value'),
                Output('size_slider', 'value'), 
                Output('selector', 'value')
                ],
              [Input('refresh-button', 'n_clicks')])     

def clearMap(n_clicks):
    if n_clicks !=0:
        pdd=["All"]
        tdd=["All"]
        ysld=[0,list(slider_dic.keys())[-1]]
        ssld=[400,170000]
        co2eld="co2_t"
        return pdd,tdd,ysld,ssld,co2eld
    
if __name__ == "__main__":
    app.run_server(debug=True,use_reloader=False)


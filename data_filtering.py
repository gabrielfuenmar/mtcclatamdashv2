# -*- coding: utf-8 -*-
"""
Created on Fri Nov 13 10:24:39 2020

@author: gabri
"""

import pandas as pd
import numpy as np

def processed_data(FLEET,portsdf,transitsdf):
    
    ##Less than 30 mins as this is the minimum number of positions to have a. Then kalman didnt work. Fix kalman to avoid this.
    ##Some didnt go thorugh kalman and have a faulty reading.
    
    ##Remove potential bunkering ops, Non in Telfer. 
    ###There is no oil operations inside Canal other than bunkering supplied.
    ###Need to refine to identify bunkering in Patsa from loading ops
    portsdf=portsdf[~(portsdf["StandardVesselType"]=="Product Tankers")&(portsdf["stop_area"]!="Telfer")]
    
    ##Containers not in PATSA in PSA and Types adjustments
    portsdf["port_name"]=np.where(portsdf["StandardVesselType"]=="Container",np.where(portsdf["stop_area"]=="Pacific - PATSA",
                              "Pacific - PSA",portsdf["stop_area"]),portsdf["stop_area"])
    
    
    ###As I dont recognize the servicing vessel, I will just keep containers, ro-ro and passagner. FOR THE MOMENT
    
    portsdf=portsdf[portsdf["StandardVesselType"].isin(FLEET)]
    
    ##Quantiles on service and waiting times to remove outliers. 10% winzorization
    ##Direct visit from after lockage.
    grouped_df=portsdf.groupby("stop_area")
    portsdf=grouped_df.apply(lambda x: x[(x.waiting_time.isnull())|((x["service_time"]>=x["service_time"].quantile(0.05))&
                                    (x["service_time"]<=x["service_time"].quantile(0.95))&
                                    (x["waiting_time"]>=x["waiting_time"].quantile(0.05))&
                                    (x["waiting_time"]<=x["waiting_time"].quantile(0.95))&
                                    (x.waiting_time.notnull()))]).reset_index(drop=True)
    
    waiting=portsdf.groupby("stop_area").waiting_time.describe()
    
    service=portsdf.groupby("stop_area").service_time.describe()
    
    ###Panama Info.
    
    transitsdf=transitsdf[transitsdf["StandardVesselType"].isin(FLEET)]
    
    
    ##Errors in values
    return portsdf,transitsdf





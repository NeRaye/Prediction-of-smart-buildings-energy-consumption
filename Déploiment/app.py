import json
from typing import Type
from flask import Flask, render_template, request 
from flask_restful import Api, Resource, reqparse
from matplotlib.pyplot import scatter 
import numpy as np
import pandas as pd
import tensorflow as tf 
import plotly
import plotly.express as px
from sqlalchemy import create_engine
import plotly.graph_objs as go
from datetime import date
from datetime import datetime, timedelta
from flask_wtf import Form
from wtforms import DateField
import psycopg2



APP= Flask(__name__)


@APP.route('/' )
def home():
  df=pd.read_sql_query('SELECT datetime_per_hour FROM data_per_1h ', con=engine, parse_dates=['datetime_per_hour'], index_col='datetime_per_hour')
  df=df[5136:]
  starthour = df.index.min().strftime("%m/%d/%Y, %H:%M:%S")
  endhour = df.index.max().strftime("%m/%d/%Y, %H:%M:%S")

  df=pd.read_sql_query('SELECT datetime_per_day FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day',
    con=engine, parse_dates=['datetime_per_day'], index_col='datetime_per_day')
  startday = df.index.min().strftime("%m/%d/%Y, %H:%M:%S")
  endday = df.index.max().strftime("%m/%d/%Y, %H:%M:%S")

  return render_template("homepage.html", dataToRender1=starthour, dataToRender2=endhour, dataToRender3=startday, dataToRender4=endday)

  
@APP.route('/GAS1', methods=['GET', 'POST'])
def GAS1():
  return render_template("indexGAS1.html")

@APP.route('/GAS1/response', methods=['GET', 'POST'])
def GAS1response():

  operation= request.form.get('selector1')
  granul=request.form.get('selector2')
  date1= request.form.get('date1')
  date2= request.form.get('date2')
  date1 = date1[0:10]+" "+date1[11:16]+ ":00"
  date2 = date2[0:10]+" "+date2[11:16]+ ":00"
  print(operation, granul, date1, date2)

  cur = conn.cursor()
  #------------------------------------------------VISUALISATION-----------------------------------------------------
  if operation== "Visualization":
    if granul=="Hour":

      cur.execute(""" SELECT datetime_per_hour,g1 FROM data_per_1h  WHERE datetime_per_hour BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000  
      df[1]=df[1].diff()

    if granul== "Day":

      cur.execute(""" SELECT datetime_per_day, g1 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
        WHERE datetime_per_day BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      

    if granul=="Week":

      cur.execute(""" SELECT datetime_per_day, g1 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
        WHERE datetime_per_day BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      df[1]=df[1].resample('W').sum()
      df=df.dropna()

      
    if granul=="Month":
      cur.execute(""" SELECT datetime_per_day, g1 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
        WHERE datetime_per_day BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      df[1]=df[1].resample('M').sum()
      df=df.dropna()

    g1_data = go.Scatter(x=df.index, y=df[1], line=go.scatter.Line(color='blue', width=0.8), opacity=0.8, name='Boiler 1')
    layout=go.Layout(title='Gas Consumption History of Boiler N°1', xaxis=dict(title='Date'),yaxis=dict(title='Boiler 1 (Mwh)', color='blue'))
    fig = go.Figure(data=g1_data,layout=layout)   
    graphJSON1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder) 
    return render_template("indexGAS1.html", graphJSON=graphJSON1)

  #------------------------------------------------Prediction-----------------------------------------------------
  if operation=="Prediction":
    #------------------------------------------------Hour-----------------------------------------------------

    if granul=="Hour":
      cur.execute(""" SELECT datetime_per_hour,g1 FROM data_per_1h  WHERE datetime_per_hour <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()   

      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
    
      duration_in_s= (edate-sdate).total_seconds()
      hours = divmod(duration_in_s, 3600)[0] #Duration in hours

      tab=np.array(df.tail(20)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/g1_1h_model.h5')
      for i in range (0,int(hours)):
          tab=tab.reshape((1,1,20))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
      
      
      index= pd.date_range(sdate,edate-timedelta(hours=1),freq= '60min')
      print(len(predictions))
      print(len(index))


    #------------------------------------------------Day-----------------------------------------------------
    if granul=="Day":
      cur.execute(""" SELECT datetime_per_day,g1 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
      WHERE datetime_per_day <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()

      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
      duration_in_s= (edate-sdate).total_seconds()
      days = divmod(duration_in_s, 86400)[0] #Duration in days

      tab=np.array(df.tail(4)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/g1_24h_model.h5')
      for i in range (0,int(days)):
          tab=tab.reshape((1,1,4))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
      
      
      index= pd.date_range(sdate,edate-timedelta(days=1),freq= 'd')
      print(len(predictions))
      print(len(index)) 
    
    #------------------------------------------------Week-----------------------------------------------------
    if granul=="Week":
      cur.execute(""" SELECT datetime_per_day,g1 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
      WHERE datetime_per_day <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      df=df[1] #before resampling
      df=df.resample('w').sum()


      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
      duration_in_s= (edate-sdate).total_seconds()
      weeks = divmod(duration_in_s, 604800)[0] #Duration in weeks

      tab=np.array(df.tail(4)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/g1_week_model.h5')
      for i in range (0,int(weeks)):
          tab=tab.reshape((1,1,4))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
         
      index= pd.date_range(sdate,edate,freq= 'W')
      print(len(predictions))
      print(len(index)) 

    #------------------------------------------------Month-----------------------------------------------------
    if granul=="Month":
      cur.execute(""" SELECT datetime_per_day,g1 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
      WHERE datetime_per_day <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      df=df[1] #before resampling
      df=df.resample('M').sum()


      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
      duration_in_s= (edate-sdate).total_seconds()
      weeks = divmod(duration_in_s, 2.628e+6)[0] #Duration in months

      tab=np.array(df.tail(2)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/g1_month_model.h5')
      for i in range (0,int(weeks)):
          tab=tab.reshape((1,1,2))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
         
      index= pd.date_range(sdate,edate,freq= 'M')
      print(len(predictions))
      print(len(index))   



    g1_data = go.Scatter(x=index, y=predictions, line=go.scatter.Line(color='blue', width=0.8), opacity=0.8, name='Boiler 1')
    layout=go.Layout(title='Gas Consumption Predition of Boiler N°1', xaxis=dict(title='Date'),yaxis=dict(title='Boiler 1 (Mwh)', color='blue'))
    fig = go.Figure(data=g1_data,layout=layout)   
    graphJSON1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder) 
    return render_template("indexGAS1.html", graphJSON=graphJSON1)
  cur.close()


@APP.route('/GAS2', methods=['GET'])
def GAS2():
  return render_template("indexGAS2.html")

@APP.route('/GAS2/response', methods=['GET', 'POST'])
def GAS2response():
  operation= request.form.get('selector1')
  granul=request.form.get('selector2')
  date1= request.form.get('date1')
  date2= request.form.get('date2')
  date1 = date1[0:10]+" "+date1[11:16]+ ":00"
  date2 = date2[0:10]+" "+date2[11:16]+ ":00"
  print(operation, granul, date1, date2)
  cur = conn.cursor()
  #------------------------------------------------VISUALISATION-----------------------------------------------------
  if operation== "Visualization":
    if granul=="Hour":

      cur.execute(""" SELECT datetime_per_hour,g2 FROM data_per_1h  WHERE datetime_per_hour BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000  
      df[1]=df[1].diff()

    if granul== "Day":

      cur.execute(""" SELECT datetime_per_day, g2 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
        WHERE datetime_per_day BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      

    if granul=="Week":

      cur.execute(""" SELECT datetime_per_day, g2 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
        WHERE datetime_per_day BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      df[1]=df[1].resample('W').sum()
      df=df.dropna()

      
    if granul=="Month":
      cur.execute(""" SELECT datetime_per_day, g2 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
        WHERE datetime_per_day BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      df[1]=df[1].resample('M').sum()
      df=df.dropna()

    g1_data = go.Scatter(x=df.index, y=df[1], line=go.scatter.Line(color='blue', width=0.8), opacity=0.8, name='Boiler 2')
    layout=go.Layout(title='Gas Consumption History of Boiler N°2', xaxis=dict(title='Date'),yaxis=dict(title='Boiler 2 (Mwh)', color='blue'))
    fig = go.Figure(data=g1_data,layout=layout)   
    graphJSON1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder) 
    return render_template("indexGAS2.html", graphJSON=graphJSON1)

  #------------------------------------------------Prediction-----------------------------------------------------
  if operation=="Prediction":
    #------------------------------------------------Hour-----------------------------------------------------

    if granul=="Hour":
      cur.execute(""" SELECT datetime_per_hour,g2 FROM data_per_1h  WHERE datetime_per_hour <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()   

      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
    
      duration_in_s= (edate-sdate).total_seconds()
      hours = divmod(duration_in_s, 3600)[0] #Duration in hours

      tab=np.array(df.tail(20)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/g2_1h_model.h5')
      for i in range (0,int(hours)):
          tab=tab.reshape((1,1,20))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
      
      
      index= pd.date_range(sdate,edate-timedelta(hours=1),freq= '60min')
      print(len(predictions))
      print(len(index))


    #------------------------------------------------Day-----------------------------------------------------
    if granul=="Day":
      cur.execute(""" SELECT datetime_per_day,g2 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
      WHERE datetime_per_day <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()

      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
      duration_in_s= (edate-sdate).total_seconds()
      days = divmod(duration_in_s, 86400)[0] #Duration in days

      tab=np.array(df.tail(4)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/g2_24h_model.h5')
      for i in range (0,int(days)):
          tab=tab.reshape((1,1,4))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
      
      
      index= pd.date_range(sdate,edate-timedelta(days=1),freq= 'd')
      print(len(predictions))
      print(len(index)) 
    
    #------------------------------------------------Week-----------------------------------------------------
    if granul=="Week":
      cur.execute(""" SELECT datetime_per_day,g2 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
      WHERE datetime_per_day <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      df=df[1] #before resampling
      df=df.resample('w').sum()


      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
      duration_in_s= (edate-sdate).total_seconds()
      weeks = divmod(duration_in_s, 604800)[0] #Duration in weeks

      tab=np.array(df.tail(4)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/g2_week_model.h5')
      for i in range (0,int(weeks)):
          tab=tab.reshape((1,1,4))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
         
      index= pd.date_range(sdate,edate,freq= 'W')
      print(len(predictions))
      print(len(index)) 

    #------------------------------------------------Month-----------------------------------------------------
    if granul=="Month":
      cur.execute(""" SELECT datetime_per_day,g2 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
      WHERE datetime_per_day <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      df=df[1] #before resampling
      df=df.resample('M').sum()


      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
      duration_in_s= (edate-sdate).total_seconds()
      weeks = divmod(duration_in_s, 2.628e+6)[0] #Duration in months

      tab=np.array(df.tail(2)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/g2_month_model.h5')
      for i in range (0,int(weeks)):
          tab=tab.reshape((1,1,2))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
         
      index= pd.date_range(sdate,edate,freq= 'M')
      print(len(predictions))
      print(len(index))   



    g1_data = go.Scatter(x=index, y=predictions, line=go.scatter.Line(color='blue', width=0.8), opacity=0.8, name='Boiler 2')
    layout=go.Layout(title='Gas Consumption Predition of Boiler N°2', xaxis=dict(title='Date'),yaxis=dict(title='Boiler 2 (Mwh)', color='blue'))
    fig = go.Figure(data=g1_data,layout=layout)   
    graphJSON1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder) 
    return render_template("indexGAS2.html", graphJSON=graphJSON1)


  cur.close()
  

@APP.route('/GAS3', methods=['GET'])
def GAS3():
  return render_template("indexGAS3.html")

@APP.route('/GAS3/response', methods=['GET', 'POST'])

def GAS3response():
  operation= request.form.get('selector1')
  granul=request.form.get('selector2')
  date1= request.form.get('date1')
  date2= request.form.get('date2')
  date1 = date1[0:10]+" "+date1[11:16]+ ":00"
  date2 = date2[0:10]+" "+date2[11:16]+ ":00"
  print(operation, granul, date1, date2)
  cur = conn.cursor()
  #------------------------------------------------VISUALISATION-----------------------------------------------------
  if operation== "Visualization":
    if granul=="Hour":

      cur.execute(""" SELECT datetime_per_hour,g3 FROM data_per_1h  WHERE datetime_per_hour BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000  
      df[1]=df[1].diff()

    if granul== "Day":

      cur.execute(""" SELECT datetime_per_day, g3 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
        WHERE datetime_per_day BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      

    if granul=="Week":

      cur.execute(""" SELECT datetime_per_day, g3 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
        WHERE datetime_per_day BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      df[1]=df[1].resample('W').sum()
      df=df.dropna()

      
    if granul=="Month":
      cur.execute(""" SELECT datetime_per_day, g3 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
        WHERE datetime_per_day BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      df[1]=df[1].resample('M').sum()
      df=df.dropna()

    g1_data = go.Scatter(x=df.index, y=df[1], line=go.scatter.Line(color='blue', width=0.8), opacity=0.8, name='Boiler 3')
    layout=go.Layout(title='Gas Consumption History of Boiler N°3', xaxis=dict(title='Date'),yaxis=dict(title='Boiler 3 (Mwh)', color='blue'))
    fig = go.Figure(data=g1_data,layout=layout)   
    graphJSON1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder) 
    return render_template("indexGAS3.html", graphJSON=graphJSON1)

  #------------------------------------------------Prediction-----------------------------------------------------
  if operation=="Prediction":
    #------------------------------------------------Hour-----------------------------------------------------

    if granul=="Hour":
      cur.execute(""" SELECT datetime_per_hour,g3 FROM data_per_1h  WHERE datetime_per_hour <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()   

      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
    
      duration_in_s= (edate-sdate).total_seconds()
      hours = divmod(duration_in_s, 3600)[0] #Duration in hours

      tab=np.array(df.tail(20)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/g3_1h_model.h5')
      for i in range (0,int(hours)):
          tab=tab.reshape((1,1,20))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
      
      
      index= pd.date_range(sdate,edate-timedelta(hours=1),freq= '60min')
      print(len(predictions))
      print(len(index))


    #------------------------------------------------Day-----------------------------------------------------
    if granul=="Day":
      cur.execute(""" SELECT datetime_per_day,g3 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
      WHERE datetime_per_day <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()

      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
      duration_in_s= (edate-sdate).total_seconds()
      days = divmod(duration_in_s, 86400)[0] #Duration in days

      tab=np.array(df.tail(4)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/g3_24h_model.h5')
      for i in range (0,int(days)):
          tab=tab.reshape((1,1,4))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
      
      
      index= pd.date_range(sdate,edate-timedelta(days=1),freq= 'd')
      print(len(predictions))
      print(len(index)) 
    
    #------------------------------------------------Week-----------------------------------------------------
    if granul=="Week":
      cur.execute(""" SELECT datetime_per_day,g3 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
      WHERE datetime_per_day <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      df=df[1] #before resampling
      df=df.resample('w').sum()


      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
      duration_in_s= (edate-sdate).total_seconds()
      weeks = divmod(duration_in_s, 604800)[0] #Duration in weeks

      tab=np.array(df.tail(4)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/g3_week_model.h5')
      for i in range (0,int(weeks)):
          tab=tab.reshape((1,1,4))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
         
      index= pd.date_range(sdate,edate,freq= 'W')
      print(len(predictions))
      print(len(index)) 

    #------------------------------------------------Month-----------------------------------------------------
    if granul=="Month":
      cur.execute(""" SELECT datetime_per_day,g3 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
      WHERE datetime_per_day <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1]*1.02264*40/ 3.6 /1000 
      df[1]=df[1].diff()
      df=df[1] #before resampling
      df=df.resample('M').sum()


      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
      duration_in_s= (edate-sdate).total_seconds()
      weeks = divmod(duration_in_s, 2.628e+6)[0] #Duration in months

      tab=np.array(df.tail(2)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/g3_month_model.h5')
      for i in range (0,int(weeks)):
          tab=tab.reshape((1,1,2))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
         
      index= pd.date_range(sdate,edate,freq= 'M')
      print(len(predictions))
      print(len(index))   



    g1_data = go.Scatter(x=index, y=predictions, line=go.scatter.Line(color='blue', width=0.8), opacity=0.8, name='Boiler 3')
    layout=go.Layout(title='Gas Consumption Predition of Boiler N°3', xaxis=dict(title='Date'),yaxis=dict(title='Boiler 3 (Mwh)', color='blue'))
    fig = go.Figure(data=g1_data,layout=layout)   
    graphJSON1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder) 
    return render_template("indexGAS3.html", graphJSON=graphJSON1)


  cur.close()

@APP.route('/ELECT', methods=['GET'])
def ELECT():
  return render_template("indexELECT.html")

@APP.route('/ELECT/response', methods=['GET', 'POST'])

def ELECTresponse():
  operation= request.form.get('selector1')
  granul=request.form.get('selector2')
  date1= request.form.get('date1')
  date2= request.form.get('date2')
  date1 = date1[0:10]+" "+date1[11:16]+ ":00"
  date2 = date2[0:10]+" "+date2[11:16]+ ":00"
  print(operation, granul, date1, date2)
  cur = conn.cursor()
  #------------------------------------------------VISUALISATION-----------------------------------------------------
  if operation== "Visualization":
    if granul=="Hour":

      cur.execute(""" SELECT datetime_per_hour,ef1 FROM data_per_1h  WHERE datetime_per_hour BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)

    if granul== "Day":

      cur.execute(""" SELECT datetime_per_day, ef1 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
        WHERE datetime_per_day BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
           

    if granul=="Week":

      cur.execute(""" SELECT datetime_per_day, ef1 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
        WHERE datetime_per_day BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1].resample('W').sum()
      df=df.dropna()

      
    if granul=="Month":
      cur.execute(""" SELECT datetime_per_day, ef1 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
        WHERE datetime_per_day BETWEEN  %s AND %s ; """, [date1, date2])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df[1]=df[1].resample('M').sum()
      df=df.dropna()

    g1_data = go.Scatter(x=df.index, y=df[1], line=go.scatter.Line(color='blue', width=0.8), opacity=0.8, name='Electricity')
    layout=go.Layout(title='Electricity Consumption History', xaxis=dict(title='Date'),yaxis=dict(title='Electricity (Kwh)', color='blue'))
    fig = go.Figure(data=g1_data,layout=layout)   
    graphJSON1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder) 
    return render_template("indexELECT.html", graphJSON=graphJSON1)

  #------------------------------------------------Prediction-----------------------------------------------------
  if operation=="Prediction":
    #------------------------------------------------Hour-----------------------------------------------------

    if granul=="Hour":
      cur.execute(""" SELECT datetime_per_hour,ef1 FROM data_per_1h  WHERE datetime_per_hour <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)     
         

      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
    
      duration_in_s= (edate-sdate).total_seconds()
      hours = divmod(duration_in_s, 3600)[0] #Duration in hours

      tab=np.array(df.tail(20)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/ef_1h_model.h5')
      for i in range (0,int(hours)):
          tab=tab.reshape((1,1,20))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
      
      
      index= pd.date_range(sdate,edate-timedelta(hours=1),freq= '60min')
      print(len(predictions))
      print(len(index))


    #------------------------------------------------Day-----------------------------------------------------
    if granul=="Day":
      cur.execute(""" SELECT datetime_per_day,ef1 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
      WHERE datetime_per_day <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)

      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
      duration_in_s= (edate-sdate).total_seconds()
      days = divmod(duration_in_s, 86400)[0] #Duration in days

      tab=np.array(df.tail(4)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/ef_24h_model.h5')
      for i in range (0,int(days)):
          tab=tab.reshape((1,1,4))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
      
      
      index= pd.date_range(sdate,edate-timedelta(days=1),freq= 'd')
      print(len(predictions))
      print(len(index)) 
    
    #------------------------------------------------Week-----------------------------------------------------
    if granul=="Week":
      cur.execute(""" SELECT datetime_per_day,ef1 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
      WHERE datetime_per_day <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df=df[1] #before resampling
      df=df.resample('w').sum()


      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
      duration_in_s= (edate-sdate).total_seconds()
      weeks = divmod(duration_in_s, 604800)[0] #Duration in weeks

      tab=np.array(df.tail(4)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/ef_week_model.h5')
      for i in range (0,int(weeks)):
          tab=tab.reshape((1,1,4))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
         
      index= pd.date_range(sdate,edate,freq= 'W')
      print(len(predictions))
      print(len(index)) 

    #------------------------------------------------Month-----------------------------------------------------
    if granul=="Month":
      cur.execute(""" SELECT datetime_per_day,ef1 FROM data_per_1h JOIN data_per_24h ON data_per_1h.datetime_per_hour= data_per_24h.datetime_per_day
      WHERE datetime_per_day <  %s ; """, [date1])
      df = pd.DataFrame(cur.fetchall())
      df=df.set_index(0, drop=True)
      df=df[1] #before resampling
      df=df.resample('M').sum()


      #get duration 
      sdate = datetime. strptime(date1, '%Y-%m-%d %H:%M:%S')
      edate= datetime. strptime(date2, '%Y-%m-%d %H:%M:%S')
      duration_in_s= (edate-sdate).total_seconds()
      weeks = divmod(duration_in_s, 2.628e+6)[0] #Duration in months

      tab=np.array(df.tail(2)) #get last 20 observation 
      predictions = []
      model= tf.keras.models.load_model('C:/Users/Rayane/Desktop/saved_models/ef_month_model.h5')
      for i in range (0,int(weeks)):
          tab=tab.reshape((1,1,2))
          prediction= model.predict(tab)
          predictions.append(prediction[0][0])
          tab=np.append(tab, prediction)
          tab=np.delete(tab,0)
         
      index= pd.date_range(sdate,edate,freq= 'M')
      print(len(predictions))
      print(len(index))   



    g1_data = go.Scatter(x=index, y=predictions, line=go.scatter.Line(color='blue', width=0.8), opacity=0.8, name='Electricity')
    layout=go.Layout(title='Electricity Consumption Predition', xaxis=dict(title='Date'),yaxis=dict(title='Electricity (Kwh)', color='blue'))
    fig = go.Figure(data=g1_data,layout=layout)   
    graphJSON1 = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder) 
    return render_template("indexELECT.html", graphJSON=graphJSON1)


  cur.close()

@APP.route('/MAJ', methods=['GET', 'POST'])
def MAJ():
  #execute models update
  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_g1_1h.py').read())
  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_g1_24h.py').read())
  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_g1_week.py').read())
  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_g1_month.py').read())

  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_g2_1h.py').read())
  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_g2_24h.py').read())
  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_g2_week.py').read())
  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_g2_month.py').read())

  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_g3_1h.py').read())
  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_g3_24h.py').read())
  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_g3_week.py').read())
  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_g3_month.py').read())

  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_ef_1h.py').read())
  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_ef_24h.py').read())
  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_ef_week.py').read())
  exec(open('C:/Users/Rayane/Desktop/Models for MAJ/model_ef_month.py').read())

  return render_template("maj.html")


if __name__== '__main__':

    engine = create_engine('postgresql://postgres:root@localhost:5432/euproject_dhw_data')
    conn = psycopg2.connect(
    user = "postgres",
    password = "root",
    host = "127.0.0.1",
    port = "5432",
    database = "euproject_dhw_data"
    )
    APP.run(debug=True, port ='1080')

  
  






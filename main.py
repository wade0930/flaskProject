from flask import Flask
from flask import render_template
from flask import request,url_for,redirect,send_file,flash,session,app
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import timedelta
from io import BytesIO
from IP import GetIP
from members import GetUsers
import cx_Oracle
import pandas as pd
import numpy as np
import xlsxwriter

import datetime
import time
import os 

app = Flask(__name__)
SecretKey = os.urandom(16).hex()
app.secret_key = SecretKey

login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.session_protection = "strong"
login_manager.login_view = 'login'
# login_manager.login_message = '請證明你並非來自黑暗草泥馬界'


class User(UserMixin):
    pass

users = GetUsers()

#設置登入時間多久自動登出
@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=5)


@login_manager.user_loader
def load_user(user_id):
    if query_user(user_id) is not None:
        curr_user =User()
        curr_user.id = user_id

        login_user(curr_user)
        return curr_user

#去memebers裡尋找會員資料
def query_user(user_id):
    for user in users:
        if user_id == user['id']:
            return user

def DateFormat(data):
    otherStyleTime = []
    for i in data['日期']:
        i = i.replace(" ","")
        timeArray = time.strptime(i, "%Y%m%d%H%M%S")
        otherStyleTime.append(time.strftime("%Y-%m-%d %H:%M:%S",timeArray))
        
    return otherStyleTime

def DataRename(data):
    data = data.rename(columns={"COIL_NO":"鋼捲號碼","STEEL_GRADE":"鋼種","FDT":"日期",
    "THICKNESS":"厚度","WIDTH":"寬度","COIL_WEIGHT":"重量","HEATED_AIR_TEMP":"空氣溫度",
    "FURN_O2_ZONE_2":"含氧量zone2","FURN_O2_ZONE_5":"含氧量zone5","FURN_O2_ZONE_8":"含氧量zone8",
    "AVG_SPEED":"平均速度","LNG_CONSUM":"瓦斯耗量","LNG_UNIT":"瓦斯單耗","TV":"TV值","STRIP_TEMP":"鋼帶溫度",
    "PRE_TEMP":"設定溫度"})
    return data

def Judege(data):
    data.loc[(data.平均速度 <60) & (data.厚度<=0.8),['備註']] = '速度<60'
    data.loc[data.瓦斯耗量 == 0 , ['備註']] = '重酸' 
    data.loc[(data.平均速度 <60) & (data.厚度<=0.8) & (data.瓦斯耗量 == 0),['備註']]='重酸&速度<60'
    data['差異溫度'] = abs(data['設定溫度'] - data['鋼帶溫度'])
    return data

def OnlyCharNum(s): 
    s2=s.lower()   
    format="abcdefghijklmnopqrstuvwxyz0123456789"
    for c in s2:
        if not c in format:
            s = s.replace(c,"")
    return s


def Web_Select(start_date,end_date):
    
    #去掉日期中間槓號
    start_date = OnlyCharNum(str(start_date)) 
    end_date = OnlyCharNum(str(end_date))
    
    conn = cx_Oracle.connect("tqcuser", "tqcuser", "100.1.1.31:1521/RP547A",encoding = "UTF-8")
    cur = conn.cursor()
    sql = """ select  SHIFT_DATE,FINISH_DATE,FINISH_TIME,--start_DATE||' '||start_TIME AS SDT,
            COIL_NO,STEEL_GRADE,FINISH_DATE||' '||FINISH_TIME AS FDT,
            ACTUAL_THICKNESS AS THICKNESS,ACTUAL_WIDTH AS WIDTH,COIL_WEIGHT,HEATED_AIR_TEMP,FURN_O2_ZONE_2,FURN_O2_ZONE_5,FURN_O2_ZONE_8,
            round(AVG_SPEED,2) AS AVG_SPEED, LNG_CONSUM AS LNG_CONSUM,
            round(LNG_CONSUM/(COIL_WEIGHT/1000),1) AS LNG_UNIT,
            round(ACTUAL_THICKNESS*AVG_SPEED,2) AS TV,
            STRIP_TEMP_ZONE_9 AS STRIP_TEMP
           ,case when ACTUAL_THICKNESS<=0.8 
                 then (
                    case when AVG_SPEED <=70                 then 1090
                         when AVG_SPEED between 70.1 and  95 then 1100
                         when AVG_SPEED between 95.1 and 110 then 1110
                         else 9999
                         end
                 )
                 else ( 
                    case when round(ACTUAL_THICKNESS*AVG_SPEED,2) <=70                 then 1090
                         when round(ACTUAL_THICKNESS*AVG_SPEED,2) between 70.1 and  80 then 1100
                         when round(ACTUAL_THICKNESS*AVG_SPEED,2) between 80.1 and  90 then 1110
                         when round(ACTUAL_THICKNESS*AVG_SPEED,2) between 90.1 and 105 then 1120
                         else 6666
                         end
                 )
                 end AS PRE_TEMP
        from    tqc.cap_pdo
        where   lng_consum >= 0
        and     to_number(finish_Date,'99999999') >= 20200211
        and finish_DATE """ 

    sql = sql +" BETWEEN "+start_date+" AND "+end_date
    cur.execute(sql)
    result = pd.read_sql(sql,conn)

    # 新增欄位
    result['差異溫度'] = ""
    result['備註'] = ""
    
    # 卸載欄位
    result = result.drop( columns =['SHIFT_DATE','FINISH_DATE','FINISH_TIME']) 

    result = DataRename(result)
    result = Judege(result)

    result = result.sort_values("日期")
    #重新排序序號
    result = result.reset_index()
    # 卸載欄位
    result = result.drop( columns =['index']) 

    result['日期'] = DateFormat(result)


    conn.close
    return result


@app.route('/login',methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        user_id = request.form.get("user_id")
        user = query_user(user_id)
        if user is not None and request.form['password'] == user['password']:
            curr_user = User()
            curr_user.id = user_id
            login_user(curr_user)
            return redirect(url_for('home'))
        error ="帳號或密碼錯誤"
    return render_template('login.html',error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return  redirect(url_for('login'))


@app.route("/home")
@app.route("/index")
@app.route("/")
@login_required
def home():
    #取得登入電腦的ip
    # ip = request.remote_addr 
    #從IP池取IP
    # IP_Pool = GetIP()
    #比對IP
    # for i in IP_Pool: 
    #     if i == ip:
    return render_template('home.html')

@app.route("/show",methods=['GET','POST'])
@login_required
def show(methods=['GET','POST']):
    if request.method == 'POST':    
        python_records=Web_Select(request.values["date_start"],request.values["date_end"])
        if request.form.get('check',type=str) == "true":
            date_dt = datetime.datetime.now()
            date_dt = date_dt.strftime("%Y%m%d_%H%M")
            filename = date_dt +"GasData.xlsx"
            
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            python_records.to_excel(writer , startrow = 0 , merge_cells = False , sheet_name = "GasData")
            workbook = writer.book
            worksheet = writer.sheets["GasData"]
            workbook.close
            writer.save()
            output.seek(0)
            return send_file(output, as_attachment=True, attachment_filename=filename)
        
        return  render_template('show.html',data=python_records)

     

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=10000)
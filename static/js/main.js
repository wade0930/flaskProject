var date = new Date();
var day = date.getDate();
var month = date.getMonth()+1; 
var LastDate = new Date();
var RightTime = LastDate.getTime();//現在時間到1970/01/01的毫秒數
LastDate.setTime(RightTime - 86400000)//減去一天的毫秒數變成昨天時間
if(month< 10 ){
    month = "0" + (date.getMonth()+1);
}

if(day < 10){
    day = "0" + (date.getDate()+1);
}
var datelast = LastDate.getFullYear() + "-" + (LastDate.getMonth()+1) + "-" + LastDate.getDate();//變字串
var datew = date.getFullYear() + "-" + month + "-" + day;
var date_start = document.querySelector('input[name="date_start"]');
var date_end = document.querySelector('input[name="date_end"]');

date_start.value = datelast;
date_end.value = datew;




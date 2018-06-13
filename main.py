from bottle import route, run,HTTPResponse,request, static_file
from datetime import datetime
import json,glob,os,math,sqlite3,secrets,string

tconnect = sqlite3.connect("threads.db")
nconnect = sqlite3.connect("nicks.db")
tcon = tconnect.cursor()
ncon = nconnect.cursor()

'''
Threads
ID Title Date ComDate ComCnt ViewCnt

Nicks
ID Name Pass

Comments
ID Date Name Body
'''

#JSONとして返す
def js_resp(jsdata):
    r = HTTPResponse(status=200, body=json.dumps(jsdata,ensure_ascii=False))
    r.set_header('Content-Type', 'application/json')
    r.set_header('Access-Control-Allow-Origin','*')
    r.set_header('Server','Yajuu-Senpai')
    return r
   
#ランダムな文字列を作成する
def gen_password():
     alphabet = string.ascii_letters + string.digits
     password = ''.join(secrets.choice(alphabet) for i in range(5)) 
     return password

'''
スレッド操作
'''
@route('/make_thread',method='POST')
def make_thread():
    #スレ名 ユーザー名 1レス 日付(サーバー側時刻) 閲覧回数(VN)
    #ID Title Date ComDate ComCnt ViewCnt
    #トリップ確認
    pschk = ncon.execute("SELECT * from nicks where Pass=?",(request.forms.user_name,)).fetchone()
    if pschk != None: name = pschk[1]
    else: name = request.forms.user_name
    #ユーザー重複確認
    chk = ncon.execute("SELECT * from nicks where Name=?",(request.forms.user_name,)).fetchone()
    if chk != None: name += " [X]"
    cm = request.forms.comment
    dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    vn = 0
    #スレッド作成
    tcon.execute("INSERT INTO threads(Title,Date,ComDate,ComCnt,ViewCnt) VALUES (?,?,?,?,?)",(request.forms.thread_name,dt,dt,1,0))
    tid = tcon.execute("SELECT MAX(ID) FROM threads").fetchone()
    #コメントテーブル作成
    cconnect = sqlite3.connect("./comments/%s.db"%(tid))
    ccon = cconnect.cursor()
    ccon.execute('CREATE TABLE "comments" ( `ID` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, `Date` TEXT NOT NULL, `Name` INTEGER NOT NULL, `Body` TEXT NOT NULL )')
    ccon.execute("INSERT INTO comments(Date,Name,Body) VALUES (?,?,?)",(dt,name,cm))
    #結果にコミットする
    cconnect.commit()
    tconnect.commit()
    return js_resp({"Message":"OK"})

@route('/list_thread',method='GET')
def list_thread():
    #指定した範囲のスレッド一覧を取る
    #?page=1 等のURLパラメータと LIMIT と OFFSET を使うことをおすすめする
    st,ed = request.query.start,request.query.end
    if st == "": st = 1
    if ed == "": ed = 10
    datas = tcon.execute("SELECT * from Threads where ID >= ? and ID <= ?",(st,ed)).fetchall()
    return js_resp(datas)

'''
レス操作
'''    
@route('/make_comment/<thread>',method='POST')
def make_comment(thread):
    if os.path.exists("./comments/%s.db"%(thread)):
        #ID Date NameID Body
        dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        #トリップ確認
        pschk = ncon.execute("SELECT * from nicks where Pass=?",(request.forms.user_name,)).fetchone()
        if pschk != None: name = pschk[1]
        else: name = request.forms.user_name
        bd = request.forms.comment
        if name != "" and bd != "" and bd != None and name != None:
            #コメントを挿入する
            cconnect = sqlite3.connect("./comments/%s.db"%(thread))
            ccon = cconnect.cursor()
            ccon.execute("INSERT INTO comments(Date,Name,Body) VALUES (?,?,?)",(dt,name,bd))
            tcon.execute("UPDATE threads set ComCnt = ComCnt + 1 where ID = ?;",(thread,))
            tcon.execute("UPDATE threads set ComDate = ? where ID = ?;",(dt,thread))
            #結果にコミットする
            cconnect.commit()
            tconnect.commit()
            return js_resp({"Message":"Success"})
        else:
            return js_resp({"Message":"Failed"})
    else:
        return js_resp({"Message":"NotFound"})     
@route('/list_comment/<thread>',method='GET')
def list_comment(thread):
    if os.path.exists("./comments/%s.db"%(thread)):
        #範囲を指定してコメント一覧を取る 本来は(以下省略)
        st,ed = request.query.start,request.query.end
        if st == "": st = 1
        if ed == "": ed = 1000
        ccon = sqlite3.connect("./comments/%s.db"%(thread))
        datas = ccon.execute("SELECT * from comments where ID >= ? and ID <= ?",(st,ed)).fetchall()
        return js_resp(datas)
    else:
        return js_resp({"Message":"NotFound"})
@route('/make_nick',method='POST')
def make_nick():
    #トリップを発行する
    nm = request.forms.user_name
    ex = ncon.execute("SELECT * from nicks where Name=?",(nm,)).fetchone()
    if ex == None:
        #パスワードが被らないようにループする(人数が増えると悲惨なことに...)
        while True:
            ps = gen_password()
            pschk = ncon.execute("SELECT * from nicks where Pass=?",(ps,)).fetchone()
            if pschk == None:
                ncon.execute("INSERT INTO nicks(Name,Pass) VALUES (?,?)",(nm,ps))
                break
        nconnect.commit()
        return js_resp({"Message":"OK","Password":ps})
    else:
        return js_resp({"Message":"AlreadyExists"})
# これ要る？？？？
@route('/read_nick',method='GET')
def read_nick():
    # ID Pass
    datas = ncon.execute("SELECT * from nicks where Pass=?",(request.query.Pass,)).fetchone()
    return js_resp(datas)

#画像やCSSはそのまま返す
@route("/<filename:path>",method="GET")
def static(filename):
    if os.path.exists("./templates/"+filename):
        return static_file(filename,root='./templates')
    else:
        return "404 NotFound ファイルが見つかりません"
# ルートは indexに飛ばす
@route("/",method="GET")
def index():
    return static_file("index.html",root='./templates')
    
run(host='localhost', port=8080, debug=True)
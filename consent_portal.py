from flask import Flask,render_template,request,send_file
import platform,socket,psutil,os,json,io,csv
app=Flask(__name__); LAST=None
def collect():
    vm=psutil.virtual_memory(); d=psutil.disk_usage("/")
    return {"Hostname":socket.gethostname(),"User":os.getenv("USER") or "Unknown","OS":platform.platform(),
    "Kernel":platform.release(),"Architecture":platform.machine(),"CPU":platform.processor() or "Unknown",
    "RAM Total":f"{vm.total/(1024**3):.2f} GB","RAM Used":f"{vm.used/(1024**3):.2f} GB",
    "Disk Total":f"{d.total/(1024**3):.2f} GB","Disk Used":f"{d.used/(1024**3):.2f} GB",
    "Local IP":socket.gethostbyname(socket.gethostname())}
@app.route("/",methods=["GET","POST"])
def home():
    global LAST
    approved=False
    if request.method=="POST" and request.form.get("consent")=="yes":
        LAST=collect(); approved=True
    return render_template("consent.html",approved=approved,data=LAST if approved else None)
@app.route("/download/json")
def dj():
    if not LAST:return "No approved report",404
    return send_file(io.BytesIO(json.dumps(LAST,indent=2).encode()),as_attachment=True,download_name="blacktiger_system.json")
@app.route("/download/csv")
def dc():
    if not LAST:return "No approved report",404
    s=io.StringIO(); w=csv.writer(s); w.writerow(["Field","Value"])
    [w.writerow([k,v]) for k,v in LAST.items()]
    return send_file(io.BytesIO(s.getvalue().encode()),as_attachment=True,download_name="blacktiger_system.csv")
app.run(host="0.0.0.0",port=8088,debug=False)
